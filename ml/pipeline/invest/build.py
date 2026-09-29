"""The investor pipeline's steps (spec §5-6): cities -> facts -> export, plus sensitivity.

Each step reads the files the previous one left in data/processed/invest/ and rewrites its own,
so any step re-runs alone (AGENTS invariant 9). `python -m pipeline.invest <step>` calls them.
"""

from __future__ import annotations

import time
from collections import Counter

import geopandas as gpd
import h3
import numpy as np
import pandas as pd
import rasterio
import shapely
import yaml
from affine import Affine
from pyproj import Transformer
from rasterio.features import rasterize

from common.fetch import MANIFESTS
from fields.national_highways.build import OUT as NH_OUT
from fields.national_highways.cell_facts import arterial_km_by_cell, nh_access_km
from fields.public_transport.cell_facts import (
    GTFS_STOPS,
    bus_feeds_by_cell,
    bus_stop_counts,
    load_stations,
    station_access_km,
)
from pipeline.invest import osm
from pipeline.invest.cities import (
    assign_places,
    label_urban_centres,
    make_slugs,
    name_pieces,
    tier_of,
)
from pipeline.invest.export import BASE_SOURCES, STATES_PATH, write_fixtures
from pipeline.invest.facts import (
    cell_centres,
    growth_pp,
    km_per_km2,
    mean_by_cell,
    name_cells,
    sum_by_cell,
)
from pipeline.invest.scores import ROOT, ScoringConfig, load_config, subscore
from pipeline.shared_layers import RAW, load_cities, load_states, read_ghsl_built

OUT = osm.OUT  # data/processed/invest
WORLDPOP = RAW / "worldpop" / "ind_ppp_2020_1km_Aggregated_UNadj.tif"
FIXTURES = ROOT / "web" / "fixtures" / "invest"
# GeoNames cities15000 lists places from 15,000 people: the whole file names pieces (spec §5), and a
# fixed property of the source, not a threshold to tune (so not in config, AGENTS invariant 8)
GEONAMES_MIN_POPULATION = 15_000
EARTH_KM = 6371.0  # mean Earth radius; a degree of latitude is EARTH_KM * pi / 180 km
# Raster pixels tested for a cell lie within this many pixels of the cell's centre. A res-7 cell
# reaches 1.4 km from its centre, and a pixel is at least 0.7 km across (WorldPop's 30" at 34° N;
# GHSL's 1 km Mollweide is sheared at India's longitudes), so 4 leaves a margin; a wider reach
# changes no cell (checked on the 2026-09 run).
REACH_PX = 4
# The sensitivity summary's definition, fixed by spec §4 ("200 random ±30 % weight perturbations")
# and plan D5 step 6 (seed); a method, not a threshold, so not in config (AGENTS invariant 8)
SEED = 20260929
DRAWS, SPREAD = 200, 0.30


def _log(msg: str, t0: float) -> None:
    print(f"[{time.monotonic() - t0:6.1f}s] {msg}", flush=True)


# --- cities -------------------------------------------------------------------------------------


def piece_table(people: np.ndarray, labels: np.ndarray, transform: Affine) -> pd.DataFrame:
    """One row per label: population (sum of people) and the population-weighted centre of its
    pixels (centroid_lat, centroid_lon)."""
    rows, cols = np.nonzero(labels)
    label, weight = labels[rows, cols], people[rows, cols]
    lon, lat = transform @ (cols + 0.5, rows + 0.5)
    n = int(labels.max(initial=0)) + 1
    pop = np.bincount(label, weights=weight, minlength=n)[1:]
    return pd.DataFrame(
        {
            "label": np.arange(1, n),
            "population": pop,
            "centroid_lat": np.bincount(label, weights=weight * lat, minlength=n)[1:] / pop,
            "centroid_lon": np.bincount(label, weights=weight * lon, minlength=n)[1:] / pop,
        }
    )


def _core_cells(labels: np.ndarray, wanted: np.ndarray, transform: Affine, res: int) -> pd.Series:
    """Per label in `wanted`: the sorted H3 cells that hold the centre of one of its pixels."""
    rows, cols = np.nonzero(np.isin(labels, wanted))
    lon, lat = transform @ (cols + 0.5, rows + 0.5)
    cells = [h3.latlng_to_cell(la, lo, res) for la, lo in zip(lat, lon, strict=True)]
    frame = pd.DataFrame({"label": labels[rows, cols], "cell": cells}).drop_duplicates()
    return frame.groupby("label")["cell"].agg(sorted)


def cities() -> None:
    """Urban centres cut at state borders become the cities (spec §5): data/processed/invest/
    pieces.parquet, plus review_pieces.csv (two or more big places, or no state) and
    review_unnamed_pieces.csv (no GeoNames place inside) for a human to read."""
    t0 = time.monotonic()
    cfg = load_config()
    c, res = cfg.raw["cities"], cfg.raw["grid"]["h3_res"]
    with rasterio.open(WORLDPOP) as src:
        people = src.read(1, masked=True).filled(0).astype("float64")
        transform = src.transform
    # WorldPop's 30" pixel is the method's nominal 1 km cell (plan D5), so the density threshold
    # applies to people per pixel. A pixel covers 0.71-0.85 km² across India: people per true km²
    # would lower the threshold by 15-29 % and chain even more of the dense rural Ganga plain.
    density = people
    states = load_states().sort_values("state").reset_index(drop=True)
    state_ids = rasterize(
        ((geom, i) for i, geom in enumerate(states.geometry, start=1)),
        out_shape=people.shape,
        transform=transform,
        all_touched=True,
        dtype="int32",
    )
    uc = c["urban_centre"]
    labels, label_state = label_urban_centres(
        density, state_ids, uc["min_density_per_km2"], uc["connectivity"]
    )
    _log(f"{len(label_state):,} urban centre pieces", t0)

    pieces = piece_table(people, labels, transform)
    pieces["state_name"] = [
        states.at[label_state[lab] - 1, "state"] if label_state[lab] else None
        for lab in pieces["label"]
    ]
    pieces = pieces[pieces["population"] >= c["min_population"]].reset_index(drop=True)
    places = assign_places(load_cities(GEONAMES_MIN_POPULATION), labels, transform)
    overrides = {int(k): str(v) for k, v in (c["name_overrides"] or {}).items()}
    pieces = name_pieces(pieces, places, overrides, c["alias_min_population"])

    big = places[(places["population"] >= c["alias_min_population"]) & (places["label"] > 0)]
    big = big.sort_values(["population", "geonameid"], ascending=[False, True])
    entries = [
        f"{n} ({p:,}; {g})"
        for n, p, g in zip(big["name"], big["population"], big["geonameid"], strict=True)
    ]
    listed = pd.Series(entries, index=big["label"]).groupby(level=0).agg("; ".join)
    pieces["big_places"] = pieces["label"].map(listed)
    unnamed, no_state = pieces["name"].isna(), pieces["state_name"].isna()
    flagged = (pieces["review"] | no_state) & ~unnamed
    review = pieces[flagged].assign(reason=np.where(no_state[flagged], "no state", "big places"))
    review_cols = ["label", "name", "state_name", "population", "big_places", "reason"]
    review[review_cols].to_csv(OUT / "review_pieces.csv", index=False)
    pieces[unnamed][["label", "state_name", "population", "centroid_lat", "centroid_lon"]].to_csv(
        OUT / "review_unnamed_pieces.csv", index=False
    )

    kept = pieces[~unnamed & ~no_state].copy()
    kept = kept.sort_values(["population", "name"], ascending=[False, True]).reset_index(drop=True)
    codes = {s["name"]: s["code"] for s in yaml.safe_load(STATES_PATH.read_text())["states"]}
    kept["state"] = kept["state_name"].map(codes)
    if kept["state"].isna().any():
        missing = sorted(kept.loc[kept["state"].isna(), "state_name"].unique())
        raise ValueError(f"state names missing from {STATES_PATH}: {missing}")
    kept["id"] = make_slugs(list(kept["name"]), list(kept["state"]))
    tiers = c["tiers"]
    kept["tier"] = [
        tier_of(p, tiers["metro_min_population"], tiers["large_min_population"])
        for p in kept["population"]
    ]
    kept["core_cells"] = kept["label"].map(
        _core_cells(labels, kept["label"].to_numpy(), transform, res)
    )
    kept.to_parquet(OUT / "pieces.parquet", index=False)

    print(
        f"\ncities: {len(kept)} of {len(pieces)} pieces of >= {c['min_population']:,} people "
        f"({unnamed.sum()} unnamed, {(no_state & ~unnamed).sum()} without a state) -> "
        f"{OUT / 'pieces.parquet'}"
    )
    dropped = pieces[unnamed].sort_values("population", ascending=False)
    print(
        f"unnamed, not exported ({len(dropped)} pieces, {dropped['population'].sum() / 1e6:.2f} M "
        f"people; all in review_unnamed_pieces.csv); largest 15:"
    )
    for r in dropped.head(15).itertuples():
        print(
            f"  {r.state_name}: {r.population:,.0f} at {r.centroid_lat:.2f}, {r.centroid_lon:.2f}"
        )
    print("per state:", dict(sorted(Counter(kept["state"]).items())))
    print(
        "top 10:",
        ", ".join(
            f"{r.name} {r.state} {r.population / 1e6:.2f} M" for r in kept.head(10).itertuples()
        ),
    )
    print(f"review ({len(review)}):")
    for r in review.itertuples():
        print(f"  {r.reason:10} {r.name} ({r.state_name}, {r.population:,.0f}): {r.big_places}")


# --- facts --------------------------------------------------------------------------------------


def area_cells(core: list[str], rings: int) -> list[str]:
    """The city's areas: every cell within `rings` steps of a core cell, sorted (spec §5)."""
    return sorted({c for cell in core for c in h3.grid_disk(cell, rings)})


def pixels_near(
    centres: pd.DataFrame, transform: Affine, crs: object, shape: tuple[int, int]
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """(rows, cols, lon, lat) of the raster pixels within REACH_PX of any centre (lat, lon), with
    each pixel centre in lon/lat. Only these pixels are reprojected and binned into cells, so the
    rest of India never is."""
    to_raster = Transformer.from_crs("EPSG:4326", crs, always_xy=True)
    x, y = to_raster.transform(centres["lon"].to_numpy(), centres["lat"].to_numpy())
    col, row = ~transform @ (np.asarray(x), np.asarray(y))
    row, col = np.floor(row).astype(int), np.floor(col).astype(int)
    near = np.zeros(shape, dtype=bool)
    for dr in range(-REACH_PX, REACH_PX + 1):
        for dc in range(-REACH_PX, REACH_PX + 1):
            r, c = row + dr, col + dc
            ok = (r >= 0) & (r < shape[0]) & (c >= 0) & (c < shape[1])
            near[r[ok], c[ok]] = True
    rows, cols = np.nonzero(near)
    x, y = transform @ (cols + 0.5, rows + 0.5)
    lon, lat = Transformer.from_crs(crs, "EPSG:4326", always_xy=True).transform(x, y)
    return rows, cols, np.asarray(lon), np.asarray(lat)


def _population(centres: pd.DataFrame, res: int) -> pd.Series:
    """WorldPop 2020 people per cell (0 where the raster has nobody), indexed by cell."""
    with rasterio.open(WORLDPOP) as src:
        people = src.read(1, masked=True).filled(0).astype("float64")
        rows, cols, lon, lat = pixels_near(centres, src.transform, src.crs, people.shape)
    per_cell = sum_by_cell(lon, lat, people[rows, cols], res)
    return per_cell.reindex(centres["cell"]).fillna(0.0)


def _built_up_growth(centres: pd.DataFrame, res: int) -> pd.Series:
    """Built-up share change 2000 -> 2020 in percentage points per cell (GHSL), indexed by cell.
    Both years are read over one window, so their pixels line up and are reprojected once."""
    margin = 0.1  # degrees around the cell centres: more than a cell's 1.4 km reach
    bounds = (
        centres["lon"].min() - margin,
        centres["lat"].min() - margin,
        centres["lon"].max() + margin,
        centres["lat"].max() + margin,
    )
    (b2000, t2000, crs2000), (b2020, t2020, crs2020) = (
        read_ghsl_built(year, bounds) for year in (2000, 2020)
    )
    if t2000 != t2020 or crs2000 != crs2020 or b2000.shape != b2020.shape:
        raise ValueError("GHSL 2000 and 2020 windows differ; growth needs one grid")
    rows, cols, lon, lat = pixels_near(centres, t2000, crs2000, b2000.shape)
    growth = growth_pp(
        mean_by_cell(lon, lat, b2000[rows, cols], res),
        mean_by_cell(lon, lat, b2020[rows, cols], res),
    )
    return growth.reindex(centres["cell"])


def shown_bus_stops(stops: pd.Series, served: set[str]) -> pd.Series:
    """Bus stops per cell as the areas show them (spec §6): the count, or 0, in cells of a city
    whose feed is shown; null everywhere else, even where a statewide feed has a stray stop, since
    that city has no bus data."""
    return stops.fillna(0.0).where(stops.index.isin(served))


def _city_bus_feeds(
    memberships: pd.DataFrame, stops: pd.Series, res: int, min_stops: int
) -> pd.DataFrame:
    """The bus feed shown for each city: the feed with the most stops in its areas, if at least
    `min_stops` (spec §6 data.bus). A second qualifying feed is printed, never dropped silently."""
    with_stops = set(stops.index[stops.notna()])
    rows = []
    for city_id, cells in memberships.groupby("city_id")["cell"]:
        if with_stops.isdisjoint(cells):
            continue
        feeds = {
            k: v for k, v in bus_feeds_by_cell(list(cells), res).items() if v["stops"] >= min_stops
        }
        if not feeds:
            continue
        chosen = max(feeds, key=lambda k: (feeds[k]["stops"], k))
        if len(feeds) > 1:
            print(f"  {city_id}: bus feeds {sorted(feeds)}; showing {chosen}")
        rows.append({"city_id": city_id, "source": chosen, **feeds[chosen]})
    cols = ["city_id", "source", "operator", "tier", "license", "fetched_at", "stops"]
    return pd.DataFrame(rows, columns=cols)


def facts() -> None:
    """Per-area facts (spec §4-5): data/processed/invest/cells.parquet (one row per area: centre,
    pop, the five raw factor values, name, bus_stops), memberships.parquet (city_id, cell) and
    city_bus.parquet (the bus feed shown per city)."""
    t0 = time.monotonic()
    cfg = load_config()
    grid, pipe = cfg.raw["grid"], cfg.raw["pipeline"]
    res = grid["h3_res"]
    pieces = pd.read_parquet(OUT / "pieces.parquet", columns=["id", "core_cells"])
    memberships = pd.DataFrame(
        [
            (city_id, cell)
            for city_id, core in zip(pieces["id"], pieces["core_cells"], strict=True)
            for cell in area_cells(list(core), grid["buffer_rings"])
        ],
        columns=["city_id", "cell"],
    )
    centres = cell_centres(sorted(set(memberships["cell"])))
    pop = _population(centres, res)
    kept = pop.index[pop >= grid["min_area_population"]]
    _log(
        f"{len(centres):,} candidate cells, {len(kept):,} with >= "
        f"{grid['min_area_population']:,} people",
        t0,
    )
    memberships = memberships[memberships["cell"].isin(kept)].reset_index(drop=True)
    if empty := sorted(set(pieces["id"]) - set(memberships["city_id"])):
        raise ValueError(
            f"cities left with no area of {grid['min_area_population']} people: {empty}"
        )

    cells = cell_centres(list(kept))
    cells["pop"] = pop.reindex(kept).to_numpy()
    cells["nh_access"] = nh_access_km(cells).to_numpy()
    cells["rail_access"] = station_access_km(cells, "rail").to_numpy()
    cells["metro_access"] = station_access_km(cells, "metro").to_numpy()
    _log("access distances", t0)
    roads = arterial_km_by_cell(res).reindex(pd.Index(kept, name="cell"), fill_value=0.0)
    cells["road_strength"] = km_per_km2(roads).to_numpy()  # OSM covers every cell: no road is 0
    _log("road strength", t0)
    cells["built_up_growth"] = _built_up_growth(cells, res).to_numpy()
    _log("built-up growth", t0)
    places = pd.read_parquet(OUT / "osm_places.parquet", columns=["lon", "lat", "name", "place"])
    cells["name"] = name_cells(cells[["cell", "lat", "lon"]], places).to_numpy()
    stops = bus_stop_counts(list(kept), res)  # NaN where no stop
    city_bus = _city_bus_feeds(memberships, stops, res, pipe["bus_feed_min_stops"])
    served = set(memberships.loc[memberships["city_id"].isin(city_bus["city_id"]), "cell"])
    cells["bus_stops"] = shown_bus_stops(stops, served).to_numpy()
    _log("names and bus stops", t0)

    cells.to_parquet(OUT / "cells.parquet", index=False)
    memberships.to_parquet(OUT / "memberships.parquet", index=False)
    city_bus.to_parquet(OUT / "city_bus.parquet", index=False)
    factors = list(cfg.factors)
    print(
        f"\nfacts: {len(cells):,} areas for {memberships['city_id'].nunique()} cities, "
        f"{len(memberships):,} memberships -> {OUT / 'cells.parquet'}"
    )
    print(
        "unobserved:",
        {f: int(cells[f].isna().sum()) for f in factors},
        f"unnamed: {int(cells['name'].isna().sum())}",
    )
    q = [0.1, 0.25, 0.5, 0.75, 0.9, 0.99]
    for f in ("road_strength", "built_up_growth"):
        print(f"{f} percentiles over areas {q}:", np.round(cells[f].quantile(q).to_numpy(), 2))
    print("bus feeds:", dict(zip(city_bus["city_id"], city_bus["source"], strict=True)))


# --- export -------------------------------------------------------------------------------------


def _bbox(cells: list[str], margin_km: float) -> tuple[float, float, float, float]:
    """(west, south, east, north) of the cells' hexagons, widened by `margin_km`."""
    lat, lon = np.array([p for c in cells for p in h3.cell_to_boundary(c)]).T
    dlat = margin_km / (EARTH_KM * np.pi / 180)
    dlon = dlat / np.cos(np.radians(np.abs(lat).max()))
    return lon.min() - dlon, lat.min() - dlat, lon.max() + dlon, lat.max() + dlat


def _highways(
    segments: gpd.GeoDataFrame, tree: shapely.STRtree, bbox: tuple, tolerance: float
) -> list:
    """Highway lines inside `bbox`, one feature per (ref, status, kind), merged and simplified."""
    hits = np.sort(tree.query(shapely.box(*bbox)))
    if not len(hits):
        return []
    part = segments.iloc[hits].assign(
        geometry=shapely.clip_by_rect(segments.geometry.iloc[hits].to_numpy(), *bbox)
    )
    out = []
    for (ref, status, kind), group in part.groupby(
        ["ref", "status", "kind"], dropna=False, sort=True
    ):
        lines = [
            g
            for g in shapely.get_parts(shapely.get_parts(group.geometry.to_numpy()))
            if g.geom_type == "LineString" and not g.is_empty
        ]
        if not lines:
            continue
        merged = shapely.simplify(shapely.line_merge(shapely.multilinestrings(lines)), tolerance)
        coords = [list(line.coords) for line in shapely.get_parts(merged) if not line.is_empty]
        props = {"ref": None if pd.isna(ref) else str(ref), "status": status, "kind": kind}
        out.append((coords, props))
    return out


def city_assets(cfg: ScoringConfig, memberships: pd.DataFrame, city_bus: pd.DataFrame) -> dict:
    """The map layers of every city (spec §6 assets), in write_fixtures' input form. Stations
    and bus stops are those inside the city's areas, so the counts on its card match the map;
    highways and toll plazas are those within the areas' bounding box plus a margin."""
    res, pipe = cfg.raw["grid"]["h3_res"], cfg.raw["pipeline"]
    stations = pd.concat([load_stations(m).assign(mode=m) for m in ("rail", "metro")])
    stations["cell"] = [
        h3.latlng_to_cell(la, lo, res)
        for la, lo in zip(stations["lat"], stations["lon"], strict=True)
    ]
    stops = pd.read_parquet(
        GTFS_STOPS, columns=["stop_lon", "stop_lat", "stop_name", "mode", "source"]
    )
    stops = stops[stops["mode"] == "bus"]
    stops["cell"] = [
        h3.latlng_to_cell(la, lo, res)
        for la, lo in zip(stops["stop_lat"], stops["stop_lon"], strict=True)
    ]
    segments = gpd.read_parquet(
        NH_OUT / "nh_segments.parquet", columns=["ref", "status", "kind", "geometry"]
    )
    segments = segments[
        segments["status"].isin(["operational", "under_construction"])
        & segments["kind"].isin(["nh_segment", "expressway_segment"])
    ].reset_index(drop=True)
    tree = shapely.STRtree(segments.geometry.to_numpy())
    plazas = gpd.read_parquet(NH_OUT / "osm_toll_plazas.parquet", columns=["name", "geometry"])
    buses = city_bus.set_index("city_id")

    out = {}
    for city_id, cells in memberships.groupby("city_id")["cell"]:
        inside = set(cells)
        here = stations[stations["cell"].isin(inside)]
        a = {
            "stations": [
                (lo, la, {"name": n, "mode": m, "source": s})
                for lo, la, n, m, s in zip(
                    here["lon"],
                    here["lat"],
                    here["name"],
                    here["mode"],
                    here["source"],
                    strict=True,
                )
            ],
            "bus_stops": None,
            "bus_source": None,
        }
        if city_id in buses.index:
            feed = buses.loc[city_id]
            mine = stops[(stops["source"] == feed["source"]) & stops["cell"].isin(inside)]
            if len(mine) != feed["stops"]:  # facts and export must count the same stops
                raise ValueError(
                    f"{city_id}: {len(mine)} stops of {feed['source']}, facts found {feed['stops']}"
                )
            a["bus_stops"] = [
                (lo, la, {"name": n})
                for lo, la, n in zip(
                    mine["stop_lon"], mine["stop_lat"], mine["stop_name"], strict=True
                )
            ]
            a["bus_source"] = {
                "source": feed["source"],
                "operator": feed["operator"],
                "tier": feed["tier"],
                "license": feed["license"],
                "fetched_at": str(feed["fetched_at"])[:10],  # a date, as the contract says
            }
        bbox = _bbox(list(inside), pipe["highway_margin_km"])
        a["highways"] = _highways(segments, tree, bbox, pipe["highway_simplify_deg"])
        box = plazas.cx[bbox[0] : bbox[2], bbox[1] : bbox[3]]
        a["toll_plazas"] = [
            (g.x, g.y, {"name": None if pd.isna(n) else str(n)})
            for g, n in zip(box.geometry, box["name"], strict=True)
        ]
        out[city_id] = a
    return out


def as_of(source_ids: list[str]) -> str:
    """The newest fetch date among the sources' manifests: re-running on the same data writes the
    same date, so the fixtures stay byte-identical. Every record's `fetched_at` is this date, so a
    source fetched earlier (OSM, WorldPop and GHSL on 2026-09-28) reads a day newer than it is;
    meta.sources names each source, and its manifest keeps the exact time."""
    return max(
        f["fetched_at"][:10]
        for s in source_ids
        for f in yaml.safe_load((MANIFESTS / f"{s}.yaml").read_text())["files"]
    )


def export() -> None:
    """Scores and assets -> web/fixtures/invest (spec §6), replacing the previous tree."""
    t0 = time.monotonic()
    cfg = load_config()
    pieces = pd.read_parquet(OUT / "pieces.parquet")
    cells = pd.read_parquet(OUT / "cells.parquet")
    memberships = pd.read_parquet(OUT / "memberships.parquet")
    city_bus = pd.read_parquet(OUT / "city_bus.parquet")
    assets = city_assets(cfg, memberships, city_bus)
    _log("assets", t0)
    feeds = {p["source"] for a in assets.values() for _, _, p in a["stations"]}
    feeds |= set(city_bus["source"])
    date = as_of([*BASE_SOURCES, *sorted(feeds - set(BASE_SOURCES))])
    write_fixtures(FIXTURES, cfg, pieces, cells, memberships, assets, date)
    files = [f for f in FIXTURES.rglob("*") if f.is_file()]
    biggest = max(files, key=lambda f: f.stat().st_size)
    total = sum(f.stat().st_size for f in files)
    _log(
        f"fixtures as of {date}: {len(files)} files, {total / 1e6:.1f} MB; largest "
        f"{biggest.relative_to(FIXTURES)} {biggest.stat().st_size / 1e6:.2f} MB -> {FIXTURES}",
        t0,
    )


# --- sensitivity --------------------------------------------------------------------------------


def city_scores(
    cfg: ScoringConfig,
    cells: pd.DataFrame,
    memberships: pd.DataFrame,
    city_ids: list[str],
    weights: np.ndarray,
) -> np.ndarray:
    """City scores for many weightings at once: rows follow `city_ids`, columns the rows of
    `weights` (factors in config order). The same arithmetic as write_fixtures -- a cell's
    weighted mean over its observed sub-scores, then the city's mean weighted by the cells'
    rounded populations -- which test_invest_export pins."""
    factors = list(cfg.factors)
    raw = cells[factors].to_numpy(dtype=float, na_value=np.nan)
    subs = np.array(
        [
            [
                np.nan if (s := subscore(cfg.factors[f], v)) is None else s
                for f, v in zip(factors, row, strict=True)
            ]
            for row in raw
        ]
    ).reshape(len(cells), len(factors))
    seen = ~np.isnan(subs)
    den = seen @ weights.T
    if (den == 0).any():
        raise ValueError("a cell has no observed factor with weight under some weighting")
    cell_score = (np.where(seen, subs, 0.0) @ weights.T) / den
    pairs = memberships[["city_id", "cell"]].drop_duplicates()
    city = pd.Index(city_ids).get_indexer(pairs["city_id"])
    pos = pd.Index(cells["cell"]).get_indexer(pairs["cell"])
    if (city < 0).any() or (pos < 0).any() or len(set(city)) != len(city_ids):
        raise ValueError("memberships must cover exactly the given cities and known cells")
    order = np.argsort(city, kind="stable")
    city, pos = city[order], pos[order]
    pop = np.round(cells["pop"].to_numpy(dtype=float))[pos]
    starts = np.flatnonzero(np.r_[True, city[1:] != city[:-1]])
    total = np.add.reduceat(cell_score[pos] * pop[:, None], starts, axis=0)
    return total / np.add.reduceat(pop, starts)[:, None]


def _top(scores: np.ndarray, ids: np.ndarray, n: int = 5) -> set:
    return {i for _, i in sorted(zip(-scores, ids, strict=True))[:n]}


def sensitivity_report(
    cfg: ScoringConfig, cities: pd.DataFrame, cells: pd.DataFrame, memberships: pd.DataFrame
) -> str:
    """Markdown: per preset, the mean share of each state's top 5 that stays in its top 5 under
    DRAWS random ±SPREAD weight changes (renormalised), and the Spearman rank correlation of city
    scores between presets (spec §4, sensitivity summary)."""
    ids, states = cities["id"].to_numpy(), cities["state"].to_numpy()
    presets = list(cfg.presets.values())
    base_w = np.array([[p.weights[f] for f in cfg.factors] for p in presets])
    base = city_scores(cfg, cells, memberships, list(ids), base_w)
    sizes = Counter(states)
    big = sorted(s for s, n in sizes.items() if n >= 5)
    rng = np.random.default_rng(SEED)
    overlap = {}
    for j, preset in enumerate(presets):
        w = base_w[j] * rng.uniform(1 - SPREAD, 1 + SPREAD, size=(DRAWS, len(cfg.factors)))
        drawn = city_scores(cfg, cells, memberships, list(ids), w / w.sum(axis=1, keepdims=True))
        for s in big:
            rows = np.flatnonzero(states == s)
            top = _top(base[rows, j], ids[rows])
            overlap[s, preset.id] = np.mean(
                [len(top & _top(drawn[rows, d], ids[rows])) / 5 for d in range(DRAWS)]
            )
    names = [p.id for p in presets]
    lines = [
        f"### Sensitivity of the city rankings ({len(ids)} cities)",
        "",
        (
            f"Mean share of each state's top 5 cities that stays in its top 5 when every preset "
            f"weight moves by a random ±{SPREAD:.0%} and the weights are renormalised ({DRAWS} "
            f"draws per preset, seed {SEED}); states with at least 5 cities."
        ),
        "",
        "| state | cities | " + " | ".join(names) + " |",
        "|---|---:|" + "---:|" * len(names),
    ]
    lines += [
        f"| {s} | {sizes[s]} | " + " | ".join(f"{overlap[s, n]:.2f}" for n in names) + " |"
        for s in big
    ]
    lines.append(
        "| **all** | "
        + f"{sum(sizes[s] for s in big)} | "
        + " | ".join(f"{np.mean([overlap[s, n] for s in big]):.2f}" for n in names)
        + " |"
    )
    ranks = [pd.Series(base[:, j]).rank().to_numpy() for j in range(len(names))]
    lines += [
        "",
        f"Spearman rank correlation of city scores between presets ({len(ids)} cities):",
        "",
        "| | " + " | ".join(names) + " |",
        "|---|" + "---:|" * len(names),
    ]
    lines += [
        f"| {a} | "
        + " | ".join(f"{np.corrcoef(ranks[i], ranks[k])[0, 1]:.2f}" for k in range(len(names)))
        + " |"
        for i, a in enumerate(names)
    ]
    return "\n".join(lines) + "\n"


def sensitivity() -> None:
    """Print the sensitivity summary and save it to data/processed/invest/sensitivity.md."""
    cfg = load_config()
    text = sensitivity_report(
        cfg,
        pd.read_parquet(OUT / "pieces.parquet", columns=["id", "state"]),
        pd.read_parquet(OUT / "cells.parquet"),
        pd.read_parquet(OUT / "memberships.parquet"),
    )
    (OUT / "sensitivity.md").write_text(text)
    print(text)
