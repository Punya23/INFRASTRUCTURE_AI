"""Per-cell fact helpers for the investor flow (spec §4-5): points onto H3 cells, built-up growth,
road density and area names. Field-specific inputs live in ml/fields/<field>/cell_facts.py."""

from __future__ import annotations

from collections.abc import Mapping
from functools import cache

import geopandas as gpd
import h3
import numpy as np
import pandas as pd
from numpy.typing import ArrayLike

from pipeline.invest.geo import nearest
from pipeline.invest.osm import place_rank
from pipeline.invest.scores import load_config

_FACT_KEYS = ("station_dedupe_m", "station_name_merge_m", "place_name_max_km")


def _check_facts_config(section: Mapping[str, object]) -> dict[str, float]:
    """The numbers of the `facts:` section of config/scoring.yaml, each a positive number."""
    bad = [
        k for k in _FACT_KEYS if not (isinstance(section.get(k), int | float) and section[k] > 0)
    ]
    if bad:
        raise ValueError(f"config/scoring.yaml facts: {bad} missing or not a positive number")
    return {k: float(section[k]) for k in _FACT_KEYS}


@cache
def facts_config() -> dict[str, float]:
    """The thresholds of the per-area facts: the `facts:` section of config/scoring.yaml, where each
    number carries its basis. The one place these numbers come from (AGENTS invariant 8)."""
    return _check_facts_config(load_config().raw.get("facts") or {})


def _cells_of(lons: ArrayLike, lats: ArrayLike, res: int) -> list[str]:
    return [h3.latlng_to_cell(la, lo, res) for la, lo in zip(lats, lons, strict=True)]


def _grouped(
    lons: ArrayLike, lats: ArrayLike, values: ArrayLike, res: int
) -> pd.api.typing.SeriesGroupBy:
    cells = pd.Index(_cells_of(lons, lats, res), name="cell")
    return pd.Series(np.asarray(values, dtype=float), index=cells).groupby(level="cell")


def cell_centres(cells: list[str]) -> pd.DataFrame:
    """DataFrame[cell, lat, lon]: the centre of each H3 cell, indexed by cell id, so that a Series
    by cell id (mean_by_cell, arterial_km_by_cell, ...) lines up with it instead of aligning to NaN
    against a RangeIndex. The index has no name: "cell" stays one ordinary column, since an index
    also called "cell" makes merge, groupby and sort_values on it raise "ambiguous" errors."""
    latlng = np.array([h3.cell_to_latlng(c) for c in cells], dtype=float).reshape(-1, 2)
    frame = pd.DataFrame({"cell": cells, "lat": latlng[:, 0], "lon": latlng[:, 1]})
    return frame.set_index("cell", drop=False).rename_axis(None)


def mean_by_cell(lons: ArrayLike, lats: ArrayLike, values: ArrayLike, res: int) -> pd.Series:
    """Mean of `values` over the points inside each H3 cell; NaN values are skipped."""
    return _grouped(lons, lats, values, res).mean()


def sum_by_cell(lons: ArrayLike, lats: ArrayLike, values: ArrayLike, res: int) -> pd.Series:
    """Sum of `values` over the points inside each H3 cell. A cell whose values are all NaN is NaN
    (unobserved), not 0."""
    return _grouped(lons, lats, values, res).sum(min_count=1)


def growth_pp(b2000_by_cell: pd.Series, b2020_by_cell: pd.Series) -> pd.Series:
    """Change in built-up share 2000 to 2020, in percentage points.

    Inputs are the mean built-up surface per GHSL pixel (m² of a 1 km², 1e6 m², pixel), by cell. A
    cell missing from either year is NaN (index alignment): unobserved, never 0.
    """
    return 100 * (b2020_by_cell - b2000_by_cell) / 1e6


def km_per_km2(km_by_cell: pd.Series) -> pd.Series:
    """Road km per km² of cell area (H3 cell areas vary a little with latitude and at pentagons)."""
    area = pd.Series([h3.cell_area(c, "km^2") for c in km_by_cell.index], index=km_by_cell.index)
    return km_by_cell / area


def name_cells(cells: pd.DataFrame, places: pd.DataFrame, max_km: float | None = None) -> pd.Series:
    """Area name per cell (spec §5): an object Series by cell id, None when no place is near.

    A place inside the cell wins: best `place_rank` (suburb, neighbourhood, quarter, village, town,
    hamlet, city), then closest to the cell centre, then name. With none inside, the nearest place
    within `max_km` of the centre (default: the configured `place_name_max_km`); with none there
    either, None. Places with an unranked `place` value or no name are never an area name. `cells`
    holds cell ids of one H3 resolution and their centres (cell, lat, lon); `places` is lon, lat,
    name, place.
    """
    cells = cells.reset_index(drop=True)  # whatever the index is, "cell" is the column
    if cells.empty:
        return pd.Series([], index=pd.Index([], name="cell"), dtype=object)
    resolutions = {h3.get_resolution(c) for c in cells["cell"]}
    if len(resolutions) != 1:
        raise ValueError(f"cells must share one H3 resolution, got {sorted(resolutions)}")
    ranks = places["place"].map(place_rank)
    usable = ranks.notna() & places["name"].notna()
    places = places[usable].assign(rank=ranks[usable]).reset_index(drop=True)
    places["cell"] = _cells_of(places["lon"], places["lat"], resolutions.pop())

    inside = places.merge(cells[["cell", "lat", "lon"]], on="cell", suffixes=("", "_centre"))
    inside["km"] = [
        h3.great_circle_distance((la, lo), (cla, clo), unit="km")
        for la, lo, cla, clo in zip(
            inside["lat"], inside["lon"], inside["lat_centre"], inside["lon_centre"], strict=True
        )
    ]
    best = inside.sort_values(["rank", "km", "name"]).drop_duplicates("cell")
    names = dict(zip(best["cell"], best["name"], strict=True))

    bare = cells[~cells["cell"].isin(set(names))].drop_duplicates("cell").reset_index(drop=True)
    if len(bare):
        points = gpd.GeoSeries(gpd.points_from_xy(places["lon"], places["lat"]), crs="EPSG:4326")
        radius = facts_config()["place_name_max_km"] if max_km is None else max_km
        pos = nearest(bare, points, radius)["pos"].dropna().astype(int)
        names.update(zip(bare.loc[pos.index, "cell"], places["name"].to_numpy()[pos], strict=True))
    return pd.Series(
        [names.get(c) for c in cells["cell"]], index=pd.Index(cells["cell"]), dtype=object
    )
