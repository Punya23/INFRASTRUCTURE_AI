"""Public-transport facts per H3 cell for the investor flow (spec §4): station access and bus stops.

Stations are the OSM rail and metro nodes that pipeline.invest.osm extracts, plus the GTFS metro
stops (HMRL, BMRCL, CMRL) from fields.public_transport.gtfs. Bus stops are shown, not scored: a
GTFS feed exists for five cities only, so a bus factor would not compare across cities.
"""

from __future__ import annotations

import unicodedata

import geopandas as gpd
import numpy as np
import pandas as pd
import shapely

from pipeline.invest import osm
from pipeline.invest.facts import facts_config, sum_by_cell
from pipeline.invest.geo import nearest_km
from pipeline.shared_layers import INDIA_CRS, PROCESSED

OSM_STATIONS = osm.OUT / "osm_stations.parquet"
GTFS_STOPS = PROCESSED / "public_transport" / "gtfs_stops.parquet"
OSM_SOURCE = "osm_india"  # the id of the OSM extract in config/sources.yaml
_MODES = ("rail", "metro")
# GTFS location_type of a row that is a stop, platform or station: blank or 0 (stop or platform) and
# 1 (station). 2 (entrance, exit, staircase, lift), 3 (generic node) and 4 (boarding area) are not.
_STOP_TYPES = ("", "0", "1")


def _points(stations: pd.DataFrame) -> gpd.GeoSeries:
    return gpd.GeoSeries(gpd.points_from_xy(stations["lon"], stations["lat"]), crs="EPSG:4326")


def _keep_one_per_cluster(stations: pd.DataFrame, within_m: float) -> np.ndarray:
    """Boolean mask over `stations`: walking them best first (OSM before GTFS, named before
    unnamed, then file order), a station stays unless one already kept lies within `within_m`."""
    n = len(stations)
    points = _points(stations).to_crs(INDIA_CRS).to_numpy()
    left, right = shapely.STRtree(points).query(points, predicate="dwithin", distance=within_m)
    other = left != right
    left, right = left[other], right[other]
    by_left = np.argsort(left, kind="stable")
    right = right[by_left]
    ends = np.searchsorted(left[by_left], np.arange(n + 1))  # right[ends[i]:ends[i + 1]] near i
    best_first = np.lexsort(
        (
            np.arange(n),
            stations["name"].isna().to_numpy(),
            (stations["source"] != OSM_SOURCE).to_numpy(),
        )
    )
    keep = np.ones(n, dtype=bool)
    for i in best_first:
        if keep[i]:
            keep[right[ends[i] : ends[i + 1]]] = False
    return keep


def _name_key(name: object) -> str:
    """A station name reduced to what identifies it: NFKC, case-folded, only letters, marks and
    digits ("Pachaiyappa's College" and "PACHAIYAPPAS  COLLEGE." agree). "" when there is no name."""
    if not isinstance(name, str):
        return ""
    folded = unicodedata.normalize("NFKC", name).casefold()
    return "".join(c for c in folded if unicodedata.category(c)[0] in "LMN")


def _gtfs_twins(stations: pd.DataFrame, within_m: float) -> np.ndarray:
    """Boolean mask over `stations`: the GTFS rows that repeat an OSM row, meaning an OSM station of
    the same normalised name lies within `within_m`. A feed puts a station hundreds of metres from
    where OSM puts its node, too far for the proximity pass. OSM rows are never merged by name."""
    is_osm = (stations["source"] == OSM_SOURCE).to_numpy()
    key = stations["name"].map(_name_key).to_numpy()
    points = _points(stations).to_crs(INDIA_CRS).to_numpy()
    gtfs_at, osm_at = np.flatnonzero(~is_osm), np.flatnonzero(is_osm)
    near_gtfs, near_osm = shapely.STRtree(points[osm_at]).query(
        points[gtfs_at], predicate="dwithin", distance=within_m
    )
    g, o = gtfs_at[near_gtfs], osm_at[near_osm]
    twin = np.zeros(len(stations), dtype=bool)
    twin[g[(key[g] == key[o]) & (key[g] != "")]] = True
    return twin


def load_stations(mode: str) -> pd.DataFrame:
    """Stations of `mode` ("rail" or "metro") as mapped, as DataFrame[lon, lat, name, source].

    "As mapped" is not "open": OSM still tags some stations under construction railway=station
    (see pipeline.invest.osm). The OSM stations of that mode, plus the GTFS metro stops and
    stations when `mode` is "metro" (not their entrances or lifts), with duplicates removed in two
    passes: stations within the configured `station_dedupe_m` of one already kept are one station
    (OSM before GTFS, named before unnamed), and a GTFS stop with the same normalised name as an OSM
    station within `station_name_merge_m` is that station. `source` is the registry id of the feed
    the survivor came from; `name` is None where it has none (a NaN would not survive JSON).
    """
    if mode not in _MODES:
        raise ValueError(f"mode must be one of {_MODES}, got {mode!r}")
    cols = ["lon", "lat", "name", "mode"]
    stations = pd.read_parquet(OSM_STATIONS, columns=cols).query("mode == @mode")
    parts = [stations.assign(source=OSM_SOURCE)]
    if mode == "metro":
        cols = ["stop_lon", "stop_lat", "stop_name", "mode", "source", "location_type"]
        gtfs = pd.read_parquet(GTFS_STOPS, columns=cols)
        is_station = (gtfs["mode"] == "metro") & gtfs["location_type"].fillna("").isin(_STOP_TYPES)
        parts.append(
            gtfs[is_station].rename(
                columns={"stop_lon": "lon", "stop_lat": "lat", "stop_name": "name"}
            )
        )
    stations = pd.concat(parts, ignore_index=True)[["lon", "lat", "name", "source"]]
    cfg = facts_config()
    stations = stations[_keep_one_per_cluster(stations, cfg["station_dedupe_m"])]
    stations = stations.reset_index(drop=True)
    stations = stations[~_gtfs_twins(stations, cfg["station_name_merge_m"])]
    stations = stations.reset_index(drop=True)
    stations["name"] = stations["name"].astype(object).where(stations["name"].notna(), None)
    return stations


def station_access_km(centres: pd.DataFrame, mode: str) -> pd.Series:
    """Km from each centre (lat, lon) to the nearest station of `mode` (see `load_stations`)."""
    return nearest_km(centres, _points(load_stations(mode)))


def _bus_stops() -> pd.DataFrame:
    cols = ["stop_lon", "stop_lat", "mode", "operator", "tier", "source", "fetched_at", "license"]
    return pd.read_parquet(GTFS_STOPS, columns=cols).query("mode == 'bus'")


def bus_stop_counts(cells: list[str], res: int) -> pd.Series:
    """GTFS bus stops inside each of `cells` (H3 resolution `res`), as floats.

    NaN where no stop is recorded: no feed for the city, or none in that cell. It is never 0 by
    default (unknown is not zero); a caller that knows the city has a feed decides to fill 0.
    """
    stops = _bus_stops()
    per_cell = sum_by_cell(stops["stop_lon"], stops["stop_lat"], np.ones(len(stops)), res)
    return per_cell.reindex(pd.Index(cells, name="cell"))


def bus_feeds_by_cell(cells: list[str], res: int) -> dict[str, dict]:
    """The bus feeds with stops inside `cells`, keyed by feed id (the registry `source`):
    {"operator", "tier", "license", "fetched_at", "stops"}, `stops` counting only those inside
    `cells`. A feed with no stop there is absent, so cells with no feed give {}."""
    wanted, feeds = set(cells), {}
    for source, feed in _bus_stops().groupby("source"):
        per_cell = sum_by_cell(feed["stop_lon"], feed["stop_lat"], np.ones(len(feed)), res)
        stops = int(per_cell[per_cell.index.isin(wanted)].sum())
        if stops:
            first = feed.iloc[0]
            feeds[source] = {
                "operator": first["operator"],
                "tier": first["tier"],
                "license": first["license"],
                "fetched_at": first["fetched_at"],
                "stops": stops,
            }
    return feeds
