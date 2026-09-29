"""Nearest-target distances for the investor facts (shared by every field's cell facts)."""

from __future__ import annotations

import geopandas as gpd
import numpy as np
import pandas as pd
import shapely

from pipeline.shared_layers import INDIA_CRS


def nearest(
    centres: pd.DataFrame, targets: gpd.GeoSeries, max_km: float | None = None
) -> pd.DataFrame:
    """Nearest target to each centre: DataFrame[km, pos] indexed like `centres`.

    `centres` has lat/lon columns (EPSG:4326); `targets` is a GeoSeries with a CRS. Distances are
    planar in EPSG:7755 (metres ÷ 1000), within 2% of the ground distance anywhere in India (the
    projection's scale factor runs from 0.98 to 1.02); `pos` is the target's position in `targets`.
    A centre with no target (none at all, or none within `max_km`) or a non-finite coordinate gets
    NaN / <NA> and never 0: an unobserved distance must not read as "right here".
    """
    km = np.full(len(centres), np.nan)
    pos = np.full(len(centres), np.nan)
    lon, lat = centres["lon"].to_numpy(dtype=float), centres["lat"].to_numpy(dtype=float)
    usable = np.isfinite(lon) & np.isfinite(lat)  # a NaN point makes GEOS raise
    if usable.any():
        points = gpd.points_from_xy(lon[usable], lat[usable], crs="EPSG:4326").to_crs(INDIA_CRS)
        tree = shapely.STRtree(targets.to_crs(INDIA_CRS).to_numpy())
        found, metres = tree.query_nearest(
            np.asarray(points),
            max_distance=None if max_km is None else max_km * 1000,
            return_distance=True,
            all_matches=False,
        )
        rows = np.flatnonzero(usable)[found[0]]
        km[rows], pos[rows] = metres / 1000, found[1]
    return pd.DataFrame({"km": km, "pos": pos}, index=centres.index).astype({"pos": "Int64"})


def nearest_km(centres: pd.DataFrame, targets: gpd.GeoSeries) -> pd.Series:
    """Km from each centre to the nearest target; NaN when there is none (see `nearest`)."""
    return nearest(centres, targets)["km"]
