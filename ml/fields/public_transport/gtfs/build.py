"""Integrate every GTFS feed in config/fields/public_transport.yaml the way the NH sources are:
registered in config/sources.yaml, fetched with a manifest, validated (fail closed per feed), stored
with provenance, linked to the NH network and toll plazas, and exported as contract fixtures.

Steps (python -m fields.public_transport.gtfs <step>):
  feeds     read + validate each feed -> data/processed/public_transport/gtfs_{stops,routes}.parquet
  link      stops near operational NHs; transit routes passing NH toll plazas
  fixtures  web/fixtures/public_transport/<feed>_{stops,routes}.geojson (≤ 5 MB each)
Reports (aggregates, committed) go to ml/fields/public_transport/gtfs/reports/.
"""

from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import pandas as pd
import shapely
import yaml

from common.fetch import MANIFESTS, load_registry
from pipeline.fixtures import write_geojson
from pipeline.gtfs import FeedError, clean_stops, read_feed, route_lines, validate_feed
from pipeline.shared_layers import INDIA_BOUNDS, INDIA_CRS, PROCESSED, RAW, ROOT

CFG = yaml.safe_load((ROOT / "config" / "fields" / "public_transport.yaml").read_text())
OUT = PROCESSED / "public_transport"
NH = PROCESSED / "national_highways"
REPORTS = Path(__file__).parent / "reports"
FIXTURES = ROOT / "web" / "fixtures" / "public_transport"
_META = ["mode", "operator", "city", "tier", "confidence"]


def _provenance(source_id: str) -> dict:
    """source, fetched_at and license for a registered, fetched source; raises if not fetched."""
    src = load_registry()[source_id]
    manifest = MANIFESTS / f"{source_id}.yaml"
    if not manifest.exists():
        raise FileNotFoundError(f"{manifest} missing — run: uv run python -m common.fetch {source_id}")
    fetched_at = yaml.safe_load(manifest.read_text())["files"][0]["fetched_at"]
    return {"source": source_id, "fetched_at": fetched_at, "license": src["license"], "path": RAW / src["dest"]}


def build_feeds() -> pd.DataFrame:
    stops_all, routes_all, issues_all, summary = [], [], [], []
    for sid, meta in CFG["feeds"].items():
        prov = _provenance(sid)
        row = {"feed": sid, **{k: meta[k] for k in _META}}
        try:
            feed = read_feed(prov["path"])
        except FeedError as e:
            issues_all.append({"feed": sid, "level": "error", "check": "structure", "count": 1, "detail": str(e)})
            summary.append({**row, "status": "rejected"})
            continue
        issues = validate_feed(feed, INDIA_BOUNDS)
        bad = sum(i["count"] for i in issues if i["check"] == "stop_bad_coordinates")
        if bad / max(len(feed["stops"]), 1) > CFG["max_bad_stop_share"]:
            issues.append({"level": "error", "check": "too_many_bad_stops", "count": bad,
                           "detail": f"> {CFG['max_bad_stop_share']:.0%} of stops"})
        issues_all += [{"feed": sid, **i} for i in issues]
        if any(i["level"] == "error" for i in issues):
            summary.append({**row, "status": "rejected"})
            continue

        base = {k: meta[k] for k in _META} | {k: prov[k] for k in ("source", "fetched_at", "license")}
        stops = clean_stops(feed, INDIA_BOUNDS)
        stops_all.append(gpd.GeoDataFrame(
            stops.rename(columns={"stop_id": "source_ref"}).assign(**base),
            geometry=gpd.points_from_xy(stops["stop_lon"], stops["stop_lat"]), crs="EPSG:4326"))
        lines = route_lines(feed, stops)
        routes = feed["routes"].merge(lines, on="route_id", how="inner")
        no_geom = len(feed["routes"]) - len(routes)
        if no_geom:  # routes without trips or resolvable stops are counted, not silently lost
            issues_all.append({"feed": sid, "level": "warning", "check": "route_no_geometry",
                               "count": no_geom, "detail": "no trip with 2+ located stops"})
        routes_all.append(gpd.GeoDataFrame(
            routes.rename(columns={"route_id": "source_ref"}).assign(**base), geometry="geometry", crs="EPSG:4326"))
        summary.append({**row, "status": "loaded", "stops": len(stops), "routes": len(routes),
                        "routes_from_shapes": int((routes["geometry_source"] == "shape").sum()),
                        "trips": len(feed["trips"]), "fetched_at": prov["fetched_at"], "license": prov["license"]})

    OUT.mkdir(parents=True, exist_ok=True)
    REPORTS.mkdir(parents=True, exist_ok=True)
    pd.concat(stops_all, ignore_index=True).to_parquet(OUT / "gtfs_stops.parquet")
    pd.concat(routes_all, ignore_index=True).to_parquet(OUT / "gtfs_routes.parquet")
    pd.DataFrame(issues_all, columns=["feed", "level", "check", "count", "detail"]).to_csv(
        REPORTS / "feed_issues.csv", index=False)
    summary = pd.DataFrame(summary)
    summary.to_csv(REPORTS / "feed_summary.csv", index=False)
    print(summary[["feed", "status", "stops", "routes", "routes_from_shapes"]].to_string(index=False))
    return summary


def link_nh() -> pd.DataFrame:
    """Per feed: stops within nh_near_km of an operational NH; bus routes passing an NH toll plaza.
    Per plaza: how many transit routes pass it (feeds listed)."""
    stops = gpd.read_parquet(OUT / "gtfs_stops.parquet").to_crs(INDIA_CRS)
    routes = gpd.read_parquet(OUT / "gtfs_routes.parquet").to_crs(INDIA_CRS)
    seg = gpd.read_parquet(NH / "nh_segments.parquet", columns=["status", "geometry"])
    nh = seg.loc[seg["status"] == "operational"].to_crs(INDIA_CRS).geometry.values
    plazas = gpd.read_parquet(NH / "osm_toll_plazas.parquet").to_crs(INDIA_CRS).reset_index(drop=True)

    _, dist = shapely.STRtree(nh).query_nearest(stops.geometry.values, return_distance=True, all_matches=False)
    stops["nh_km"] = dist / 1000
    # road modes only: metro lines run over or beside highway plazas without paying tolls
    road = routes[routes["mode"] == "bus"].reset_index(drop=True)
    hit = shapely.STRtree(plazas.geometry.values).query(road.geometry.values, predicate="dwithin",
                                                        distance=CFG["toll_route_m"])
    pairs = pd.DataFrame({"route": hit[0], "plaza": hit[1]})
    pairs["feed"] = road["source"].values[pairs["route"]]

    near = CFG["nh_near_km"]
    by_feed = pd.DataFrame({
        "stops": stops.groupby("source").size(),
        f"stops_within_{near:g}km_of_nh": stops[stops["nh_km"] <= near].groupby("source").size(),
        "median_stop_nh_km": stops.groupby("source")["nh_km"].median().round(2),
        "routes": routes.groupby("source").size(),
        "routes_passing_toll_plaza": pairs.groupby("feed")["route"].nunique(),
        "toll_plazas_on_routes": pairs.groupby("feed")["plaza"].nunique(),
    }).fillna(0)
    by_feed[f"share_stops_within_{near:g}km_of_nh"] = (
        by_feed[f"stops_within_{near:g}km_of_nh"] / by_feed["stops"]).round(3)
    by_feed.index.name = "feed"
    by_feed.to_csv(REPORTS / "nh_toll_link_by_feed.csv")

    per_plaza = pairs.groupby("plaza").agg(transit_routes=("route", "nunique"),
                                           feeds=("feed", lambda f: ";".join(sorted(set(f)))))
    per_plaza = plazas.loc[per_plaza.index, ["node_id", "ihmcl_code", "name", "state"]].join(per_plaza)
    per_plaza.sort_values("transit_routes", ascending=False).to_csv(
        REPORTS / "toll_plazas_on_transit_routes.csv", index=False)
    print(by_feed.to_string())
    return by_feed


def write_fixtures() -> None:
    stops = gpd.read_parquet(OUT / "gtfs_stops.parquet")
    routes = gpd.read_parquet(OUT / "gtfs_routes.parquet")
    for sid in CFG["feeds"]:
        s = stops[stops["source"] == sid]
        if s.empty:
            continue
        write_geojson(gpd.GeoDataFrame({
            "id": "transit_stop:" + sid + ":" + s["source_ref"], "field": "public_transport",
            "kind": "transit_stop", "name": s.get("stop_name"), "ref": None,
            "status": "operational", "opened_on": None, "expected_completion": None,
            "agency": s["operator"], "source": sid, "confidence": s["confidence"], "mode": s["mode"],
            "tier": s["tier"], "geometry": s.geometry.values}, crs="EPSG:4326"), FIXTURES / f"{sid}_stops.geojson")
        r = routes[routes["source"] == sid]
        ref = r["route_short_name"] if "route_short_name" in r else pd.Series(None, index=r.index)
        write_geojson(gpd.GeoDataFrame({
            "id": "transit_route:" + sid + ":" + r["source_ref"], "field": "public_transport",
            "kind": "transit_route", "name": r.get("route_long_name"),
            "ref": ref.replace("", None), "status": "operational", "opened_on": None,
            "expected_completion": None, "agency": r["operator"], "source": sid, "confidence": r["confidence"],
            "mode": r["mode"], "tier": r["tier"], "geometry_source": r["geometry_source"],
            "geometry": r.geometry.simplify(CFG["route_simplify_deg"]).values}, crs="EPSG:4326"),
            FIXTURES / f"{sid}_routes.geojson")
