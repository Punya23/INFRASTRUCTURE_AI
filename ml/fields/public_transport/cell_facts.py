"""Public-transport facts per H3 cell for the investor flow (spec §4): station access and bus stops.

Stations are the OSM rail and metro nodes that pipeline.invest.osm extracts, plus the GTFS metro
stops (HMRL, BMRCL, CMRL) from fields.public_transport.gtfs. Bus stops are shown, not scored: a
GTFS feed exists for five cities only, so a bus factor would not compare across cities.
"""

from __future__ import annotations

import geopandas as gpd
import numpy as np
import pandas as pd
import shapely

from pipeline.invest import osm
from pipeline.invest.facts import sum_by_cell
from pipeline.invest.geo import nearest_km
from pipeline.shared_layers import INDIA_CRS, PROCESSED

OSM_STATIONS = osm.OUT / "osm_stations.parquet"
GTFS_STOPS = PROCESSED / "public_transport" / "gtfs_stops.parquet"
OSM_SOURCE = "osm_india"  # the id of the OSM extract in config/sources.yaml
_MODES = ("rail", "metro")
# GTFS location_type of a row that is a stop, platform or station: blank or 0 (stop or platform) and
# 1 (station). 2 (entrance, exit, staircase, lift), 3 (generic node) and 4 (boarding area) are not.
_STOP_TYPES = ("", "0", "1")
# OSM maps one interchange as several nodes (four "District Court" nodes within 200 m in Pune) and
# GTFS lists a stop per platform or entrance; stations closer than this are one — team judgment,
# 2026-09-29 (a station building is under 150 m across; adjacent stations are 400 m apart or more).
DEDUP_M = 150


def _points(stations: pd.DataFrame) -> gpd.GeoSeries:
    return gpd.GeoSeries(gpd.points_from_xy(stations["lon"], stations["lat"]), crs="EPSG:4326")


def _keep_one_per_cluster(stations: pd.DataFrame) -> np.ndarray:
    """Boolean mask over `stations`: walking them best first (OSM before GTFS, named before
    unnamed, then file order), a station stays unless one already kept lies within DEDUP_M."""
    n = len(stations)
    points = _points(stations).to_crs(INDIA_CRS).to_numpy()
    left, right = shapely.STRtree(points).query(points, predicate="dwithin", distance=DEDUP_M)
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


def load_stations(mode: str) -> pd.DataFrame:
    """Operating stations of `mode` ("rail" or "metro") as DataFrame[lon, lat, name, source].

    The OSM stations of that mode, plus the GTFS metro stops and stations when `mode` is "metro"
    (not their entrances or lifts), with near-duplicates removed (DEDUP_M). `source` is the registry
    id of the feed the survivor came from; `name` is None where it has none (a NaN would not
    survive JSON).
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
    stations = stations[_keep_one_per_cluster(stations)].reset_index(drop=True)
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
