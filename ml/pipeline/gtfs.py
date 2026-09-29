"""Read and validate any GTFS static feed (shared by every field that uses transit data).

read_feed() loads the tables the platform needs with ids kept as strings ("0012" stays "0012").
validate_feed() returns issues instead of dropping rows: structural problems are errors (the caller
rejects the whole feed), row problems are warnings with counts, and the rows they name are excluded
explicitly by clean_stops(). route_lines() builds one line per route from shapes.txt, or from the stop
sequence of the route's longest trip when a feed ships no shapes.
"""

from __future__ import annotations

import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
import shapely

REQUIRED = {
    "stops": ["stop_id", "stop_lat", "stop_lon"],
    "routes": ["route_id"],
    "trips": ["route_id", "trip_id"],
    "stop_times": ["trip_id", "stop_id", "stop_sequence"],
}
OPTIONAL = {"shapes": ["shape_id", "shape_pt_lat", "shape_pt_lon", "shape_pt_sequence"]}
_KEEP = {
    "stops": ["stop_id", "stop_name", "stop_lat", "stop_lon", "location_type", "parent_station"],
    "routes": ["route_id", "agency_id", "route_short_name", "route_long_name", "route_type"],
    "trips": ["route_id", "trip_id", "shape_id", "direction_id"],
    "stop_times": ["trip_id", "stop_id", "stop_sequence"],
    "shapes": ["shape_id", "shape_pt_lat", "shape_pt_lon", "shape_pt_sequence"],
}


class FeedError(ValueError):
    """The feed is structurally unusable (missing file or column)."""


def read_feed(path: Path) -> dict[str, pd.DataFrame]:
    """GTFS tables from a zip (files may sit in a subfolder). Raises FeedError if a required
    file or column is missing."""
    feed = {}
    with zipfile.ZipFile(path) as z:
        names = {Path(n).name: n for n in z.namelist() if n.endswith(".txt")}
        for table in [*REQUIRED, *OPTIONAL]:
            name = names.get(f"{table}.txt")
            if name is None:
                if table in REQUIRED:
                    raise FeedError(f"{path.name}: missing {table}.txt")
                continue
            with z.open(name) as f:
                df = pd.read_csv(f, dtype=str, keep_default_na=False, encoding="utf-8-sig",
                                 usecols=lambda c, t=table: c.strip() in _KEEP[t])
            df.columns = [c.strip() for c in df.columns]
            need = (REQUIRED | OPTIONAL)[table]
            missing = [c for c in need if c not in df.columns]
            if missing:
                raise FeedError(f"{path.name}: {table}.txt lacks {missing}")
            feed[table] = df.apply(lambda s: s.str.strip())
    return feed


def validate_feed(feed: dict[str, pd.DataFrame], bounds: tuple[float, float, float, float]) -> list[dict]:
    """Issues as {level, check, count, detail}. level 'error' means reject the feed."""
    issues = []

    def add(level: str, check: str, count: int, detail: str = "") -> None:
        if count:
            issues.append({"level": level, "check": check, "count": int(count), "detail": detail})

    for table, key in (("stops", "stop_id"), ("routes", "route_id"), ("trips", "trip_id")):
        add("error", f"duplicate_{key}", feed[table][key].duplicated().sum())
        add("error", f"empty_{key}", (feed[table][key] == "").sum())
    stops, trips, st = feed["stops"], feed["trips"], feed["stop_times"]
    add("warning", "stop_bad_coordinates", (~_valid_coords(stops, bounds)).sum(),
        f"outside lon/lat box {bounds} or not numeric")
    add("warning", "trip_unknown_route", (~trips["route_id"].isin(feed["routes"]["route_id"])).sum())
    add("warning", "stop_time_unknown_trip", (~st["trip_id"].isin(trips["trip_id"])).sum())
    add("warning", "stop_time_unknown_stop", (~st["stop_id"].isin(stops["stop_id"])).sum())
    add("warning", "route_without_trips", (~feed["routes"]["route_id"].isin(trips["route_id"])).sum())
    return issues


def _valid_coords(stops: pd.DataFrame, bounds) -> pd.Series:
    lon = pd.to_numeric(stops["stop_lon"], errors="coerce")
    lat = pd.to_numeric(stops["stop_lat"], errors="coerce")
    minx, miny, maxx, maxy = bounds
    return lon.between(minx, maxx) & lat.between(miny, maxy)


def clean_stops(feed: dict[str, pd.DataFrame], bounds) -> pd.DataFrame:
    """Stops with valid coordinates as floats (the excluded ones are counted by validate_feed)."""
    stops = feed["stops"][_valid_coords(feed["stops"], bounds)].copy()
    stops["stop_lon"] = stops["stop_lon"].astype(float)
    stops["stop_lat"] = stops["stop_lat"].astype(float)
    return stops


def route_lines(feed: dict[str, pd.DataFrame], stops: pd.DataFrame) -> pd.DataFrame:
    """One line per route: route_id, geometry, geometry_source ('shape' or 'stop_sequence').
    Uses the route's longest trip; its shape when the feed has one, else its stop sequence."""
    st = feed["stop_times"].assign(seq=pd.to_numeric(feed["stop_times"]["stop_sequence"], errors="coerce"))
    trips = feed["trips"].merge(st.groupby("trip_id").size().rename("n_stops"), on="trip_id")
    longest = trips.sort_values("n_stops", ascending=False).drop_duplicates("route_id")
    lines = []
    shapes = feed.get("shapes")
    if shapes is not None and "shape_id" in longest and (longest["shape_id"] != "").any():
        pts = shapes.assign(seq=pd.to_numeric(shapes["shape_pt_sequence"], errors="coerce"),
                            x=pd.to_numeric(shapes["shape_pt_lon"], errors="coerce"),
                            y=pd.to_numeric(shapes["shape_pt_lat"], errors="coerce")).dropna(subset=["seq", "x", "y"])
        coords = {sid: g.sort_values("seq")[["x", "y"]].to_numpy()
                  for sid, g in pts[pts["shape_id"].isin(longest["shape_id"])].groupby("shape_id")}
        for route_id, shape_id in zip(longest["route_id"], longest["shape_id"], strict=True):
            if shape_id in coords and len(coords[shape_id]) >= 2:
                lines.append((route_id, shapely.linestrings(coords[shape_id]), "shape"))
    done = {r for r, _, _ in lines}
    xy = stops.set_index("stop_id")[["stop_lon", "stop_lat"]]
    todo = longest[~longest["route_id"].isin(done)]
    seqs = st[st["trip_id"].isin(todo["trip_id"]) & st["stop_id"].isin(xy.index)].sort_values(["trip_id", "seq"])
    by_trip = {t: xy.loc[g["stop_id"]].to_numpy() for t, g in seqs.groupby("trip_id")}
    for route_id, trip_id in zip(todo["route_id"], todo["trip_id"], strict=True):
        c = by_trip.get(trip_id)
        if c is not None and len(np.unique(c, axis=0)) >= 2:
            lines.append((route_id, shapely.linestrings(c), "stop_sequence"))
    return pd.DataFrame(lines, columns=["route_id", "geometry", "geometry_source"])
