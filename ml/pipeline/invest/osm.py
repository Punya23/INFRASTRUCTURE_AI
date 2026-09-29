"""OSM point features for the investor flow: operating rail/metro stations and named places.

One streaming DuckDB pass over the India PBF (same pattern as fields/national_highways/build.py)
writes two small files that the area facts read:

  osm_stations.parquet  node_id, lon, lat, name, mode   mode is "metro" or "rail"
  osm_places.parquet    node_id, lon, lat, name, place  ranked localities that have a name

Both come from one source — osm_india (data/manifests/osm_india.yaml), ODbL-1.0, © OpenStreetMap
contributors — so provenance is attached when the records reach the fixtures (export.py), not stored
per row here.
"""

from __future__ import annotations

import math
import shutil

import duckdb
import pandas as pd

from pipeline.shared_layers import PROCESSED, RAW

PBF = RAW / "osm" / "india-latest.osm.pbf"
OUT = PROCESSED / "invest"

# Lower rank = better area name (spec §5): a locality beats a settlement, and a city is used only
# when nothing finer lies inside the cell. Any other place=* value (farm, locality, ...) is not an
# area name.
_PLACE_RANK = {
    "suburb": 1,
    "neighbourhood": 2,
    "quarter": 3,
    "village": 4,
    "town": 5,
    "hamlet": 6,
    "city": 7,
}
_METRO = ("subway", "light_rail", "monorail")  # both a station=<x> value and an <x>=yes flag
# Tags that mark a node as not (yet, or no longer) an operating station: <state>=<anything but no>
# (disused=yes, construction=station) or <state>:railway=... (construction:railway=station).
# Measured on the 2026-09 PBF: under-construction metro stations (Pune, Surat, Hyderabad) still
# carry railway=station. Only :railway is matched; was:name, for one, is just a former name.
_LIFECYCLE_KEYS = tuple(
    key
    for state in ("disused", "abandoned", "construction", "proposed", "was")
    for key in (state, f"{state}:railway")
)

# Sanity bounds on the extracted counts (team judgment, 2026-09-29). Outside them the PBF or a
# filter is wrong, and the run raises instead of publishing. Measured on the 2026-09-28 PBF:
# rail 9,281, metro 867, places 299,335.
_BOUNDS = {"rail": (5_000, 20_000), "metro": (400, 2_500), "places": (200_000, math.inf)}

_NAME = "coalesce(nullif(trim(tags['name:en']), ''), nullif(trim(tags['name']), ''))"  # spec §5
_STATION = "(tags['railway'] IN ('station', 'halt') OR tags['public_transport'] = 'station')"
_PLACE = "tags['place'] IN (" + ", ".join(f"'{p}'" for p in _PLACE_RANK) + ")"


def classify_station(tags: dict[str, str]) -> str | None:
    """'metro' (subway, light rail, monorail), 'rail' (heavy or suburban) or None.

    A station is a railway=station|halt node, or a node with no railway tag that is
    public_transport=station and names its rail mode (bus and ferry stations share that tag).
    A railway=proposed|construction|subway_entrance node is never one, whatever else it carries,
    and neither is a node marked disused, abandoned, proposed or under construction.
    """
    railway = tags.get("railway")
    is_station = railway in ("station", "halt") or (
        railway is None and tags.get("public_transport") == "station"
    )
    if not is_station or any(tags.get(k, "no") != "no" for k in _LIFECYCLE_KEYS):
        return None
    if tags.get("station") in _METRO or any(tags.get(k) == "yes" for k in _METRO):
        return "metro"
    return "rail" if railway or tags.get("train") == "yes" else None


def place_rank(place: str) -> int | None:
    """Rank of a place=* value as an area name (lower is better); None if it is not a locality."""
    return _PLACE_RANK.get(place)


def _split(con: duckdb.DuckDBPyConnection) -> tuple[pd.DataFrame, pd.DataFrame]:
    """The scanned `cand` table (node_id, lon, lat, tags) as (stations, places) frames.

    Stations without a name stay (they still count for access distance); places without one are
    dropped, since a place only matters as a name. Sorted by node id, so re-runs write identical
    files.
    """
    stations = con.execute(f"""
        SELECT node_id, lon, lat, {_NAME} AS name, tags FROM cand WHERE {_STATION} ORDER BY node_id
    """).df()
    stations["mode"] = [classify_station(t) for t in stations.pop("tags")]
    places = con.execute(f"""
        SELECT node_id, lon, lat, {_NAME} AS name, tags['place'] AS place FROM cand
        WHERE {_PLACE} AND {_NAME} IS NOT NULL ORDER BY node_id
    """).df()
    return stations.dropna(subset=["mode"]).reset_index(drop=True), places


def _check_counts(stations: pd.DataFrame, places: pd.DataFrame) -> dict[str, int]:
    """Counts by kind; raises RuntimeError with the numbers when any is outside _BOUNDS."""
    counts = {
        "rail": int((stations["mode"] == "rail").sum()),
        "metro": int((stations["mode"] == "metro").sum()),
        "places": len(places),
    }
    if any(not lo <= counts[k] <= hi for k, (lo, hi) in _BOUNDS.items()):
        raise RuntimeError(f"implausible OSM node counts {counts}; expected within {_BOUNDS}")
    return counts


def _publish(frames: dict[str, pd.DataFrame]) -> None:
    """Write every file under a temp name, then rename them all: a failed write leaves the previous
    outputs untouched, and a reader never sees a stations/places pair from different runs."""
    staged = []
    for name, df in frames.items():
        tmp = OUT / f"{name}.tmp"
        df.to_parquet(tmp, index=False)
        staged.append((tmp, OUT / name))
    for tmp, final in staged:
        tmp.replace(final)


def extract() -> None:
    """Scan the PBF once and write osm_stations.parquet and osm_places.parquet (idempotent)."""
    if not PBF.exists():
        raise FileNotFoundError(f"{PBF} missing — run: cd ml && uv run python -m common.fetch")
    OUT.mkdir(parents=True, exist_ok=True)
    tmp = OUT / "_duckdb_tmp"
    try:
        with duckdb.connect() as con:
            con.execute("INSTALL spatial; LOAD spatial;")
            # the scan peaks near 0.4 GB; the cap only keeps it from starving other jobs
            con.execute(
                f"SET temp_directory='{tmp}'; SET memory_limit='4GB'; "
                "SET preserve_insertion_order=false"
            )
            con.execute(f"""
                CREATE TABLE cand AS
                SELECT id AS node_id, lon, lat, tags FROM ST_ReadOSM('{PBF}')
                WHERE kind = 'node' AND ({_STATION} OR {_PLACE})
            """)
            stations, places = _split(con)
            n_station_tagged, n_places = con.execute(f"""
                SELECT count(*) FILTER (WHERE {_STATION}), count(*) FILTER (WHERE {_PLACE})
                FROM cand
            """).fetchone()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    counts = _check_counts(stations, places)
    _publish({"osm_stations.parquet": stations, "osm_places.parquet": places})
    print(  # what the filters dropped is reported, never silent (AGENTS invariant 2)
        f"osm: {counts}; skipped {n_station_tagged - len(stations)} of {n_station_tagged} "
        f"station-tagged nodes (bus/ferry, unbuilt, disused) and {n_places - len(places)} of "
        f"{n_places} ranked places (no name) -> {OUT}"
    )
