"""National Highways analysis (docs/fields/national-highways.md — EDA plan, geospatial metrics).

run_all() writes tables to data/processed/national_highways/analysis/. write_fixtures() writes the
UI fixtures: geometry comes from OSM only; NHAI data appears only as aggregates (ADR-0014).
All metrics are descriptive — no forecasting (ADR-0003).
"""

from __future__ import annotations

import json
import re

import geopandas as gpd
import h3
import networkx as nx
import numpy as np
import pandas as pd
import pdfplumber
import pyproj
import shapely
import yaml

from fields.national_highways.build import OUT, geodesic_km
from fields.national_highways.normalize import (
    lane_band,
    parse_indian_number,
    parse_year,
    road_lanes,
)
from pipeline.fixtures import write_geojson
from pipeline.shared_layers import (
    INDIA_CRS,
    RAW,
    ROOT,
    load_cities,
    load_population_points,
    load_states,
    read_ghsl_built,
)

A = OUT / "analysis"
FIXTURES = ROOT / "web" / "fixtures" / "national_highways"
CFG = yaml.safe_load((ROOT / "config" / "fields" / "national_highways.yaml").read_text())
EQUAL_AREA = "ESRI:102028"  # Asia South Albers equal-area conic — for state areas


# --------------------------------------------------------------------------- inputs
def segments() -> gpd.GeoDataFrame:
    return gpd.read_parquet(OUT / "nh_segments.parquet")


def nhai_network() -> gpd.GeoDataFrame:
    return gpd.read_parquet(OUT / "nhai_network.parquet")


def official() -> pd.DataFrame:
    return pd.read_csv(OUT / "official_state_nh_length.csv")


def _pipeline_lines(seg: gpd.GeoDataFrame) -> gpd.GeoSeries:
    """Lines not yet open: OSM construction/proposed ways + NHAI stretches with a target FY."""
    osm = seg.loc[seg["status"] != "operational", "geometry"]
    net = nhai_network()
    nhai = net.loc[net["status"] == "under_construction", "geometry"].explode(index_parts=False)
    return gpd.GeoSeries(pd.concat([osm, nhai], ignore_index=True), crs="EPSG:4326")


# --------------------------------------------------------------------------- 01 inventory
def coverage_by_state() -> pd.DataFrame:
    """OSM and NHAI NH length per state vs the official MoRTH total (the coverage report)."""
    seg = segments()
    op = seg[seg["status"] == "operational"]
    net = nhai_network()
    nhai_nh = net[(net["road_type"] == "National Highway") & (net["status"] == "operational")]
    df = official()[["state", "length_km"]].rename(columns={"length_km": "official_km"})
    df = df.merge(op[op["owner_level"] == "national"].groupby("state")["eff_km"].sum().rename("osm_nh_km"),
                  on="state", how="outer")
    df = df.merge(op[op["owner_level"] != "national"].groupby("state")["eff_km"].sum()
                  .rename("osm_other_expressway_km"), on="state", how="left")
    df = df.merge(nhai_nh.groupby("state")["length_km"].sum().rename("nhai_nh_km"), on="state", how="left")
    df = df.fillna(0.0)
    df["osm_ratio"] = df["osm_nh_km"] / df["official_km"].replace(0, np.nan)
    df["nhai_ratio"] = df["nhai_nh_km"] / df["official_km"].replace(0, np.nan)
    total = df.drop(columns="state").sum(numeric_only=True)
    total["osm_ratio"] = total["osm_nh_km"] / total["official_km"]
    total["nhai_ratio"] = total["nhai_nh_km"] / total["official_km"]
    df = pd.concat([df, pd.DataFrame([{"state": "India", **total.to_dict()}])], ignore_index=True)
    return df.sort_values("official_km", ascending=False)


def completeness_by_state() -> pd.DataFrame:
    """Share of operational NH length (effective km) carrying each attribute."""
    op = segments().query("status == 'operational'").copy()
    for col in ("lanes", "surface", "maxspeed", "name"):
        op[f"has_{col}"] = op[col].notna()
    op["has_ref"] = ~op["ref_missing"]
    cols = ["has_ref", "has_lanes", "has_surface", "has_maxspeed", "has_name"]
    weighted = op[cols].mul(op["eff_km"], axis=0)
    by_state = weighted.groupby(op["state"]).sum().div(op.groupby("state")["eff_km"].sum(), axis=0)
    overall = weighted.sum() / op["eff_km"].sum()
    by_state.loc["India"] = overall
    return by_state.round(3)


def lane_mix_by_state() -> pd.DataFrame:
    """Km by lane band: OSM (tagged ways only, both carriageways counted) and NHAI (completed NH)."""
    op = segments().query("status == 'operational'").copy()
    op["band"] = [lane_band(n) for n in road_lanes(op["lanes"], op["weight"])]
    osm = op.pivot_table(index="state", columns="band", values="eff_km", aggfunc="sum", fill_value=0)
    net = nhai_network().query("status == 'operational' and road_type == 'National Highway'").copy()
    net["band"] = net["lane_statu"].map(lane_band)
    nhai = net.pivot_table(index="state", columns="band", values="length_km", aggfunc="sum", fill_value=0)
    out = pd.concat({"osm": osm, "nhai": nhai}, axis=1).fillna(0)
    out.loc["India"] = out.sum()
    return out.round(0)


def toll_coverage_by_state() -> pd.DataFrame:
    """IHMCL plazas vs OSM plazas (booth clusters near an NH) per state, and how many match by name."""
    ihmcl = pd.read_csv(OUT / "ihmcl_plazas.csv", dtype={"code": str})
    plazas = gpd.read_parquet(OUT / "osm_toll_plazas.parquet")
    df = pd.DataFrame({
        "ihmcl_plazas": ihmcl.groupby("state").size(),
        "osm_plazas": plazas.groupby("state").size(),
        "osm_named": plazas[plazas["key"].fillna("") != ""].groupby("state").size(),
        "matched_by_name": plazas[plazas["ihmcl_code"].notna()].groupby("state").size(),
    }).fillna(0).astype(int)
    df.loc["India"] = df.sum()
    df["osm_to_ihmcl"] = (df["osm_plazas"] / df["ihmcl_plazas"].replace(0, np.nan)).round(3)
    return df.sort_values("ihmcl_plazas", ascending=False)


# --------------------------------------------------------------------------- 04 access
def _nearest_km(points_m: np.ndarray, lines_m: np.ndarray) -> np.ndarray:
    tree = shapely.STRtree(lines_m)
    _, dist = tree.query_nearest(points_m, return_distance=True, all_matches=False)
    return dist / 1000


def access() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Distance from every populated 1 km pixel to the nearest operational NH/expressway, today and
    with the pipeline added. Returns (pixels, by_state)."""
    seg = segments()
    now_lines = seg.loc[seg["status"] == "operational", "geometry"].to_crs(INDIA_CRS).simplify(20).values
    pipe_lines = _pipeline_lines(seg).to_crs(INDIA_CRS).simplify(20).values
    pop = load_population_points()
    pts = gpd.GeoDataFrame(pop, geometry=gpd.points_from_xy(pop["lon"], pop["lat"]), crs="EPSG:4326")
    states = load_states()
    joined = gpd.sjoin(pts, states, how="left", predicate="within")
    pts["state"] = joined.loc[~joined.index.duplicated(), "state"].values
    pts_m = pts.geometry.to_crs(INDIA_CRS).values
    pts["d_now_km"] = _nearest_km(pts_m, now_lines)
    pts["d_future_km"] = np.minimum(pts["d_now_km"], _nearest_km(pts_m, pipe_lines))
    pixels = pd.DataFrame(pts.drop(columns="geometry"))

    bands = CFG["access_bands_km"]
    target = CFG["access_target_km"]

    def summarize(g: pd.DataFrame) -> pd.Series:
        w = g["pop"]
        row = {"population": w.sum(), "mean_km_now": np.average(g["d_now_km"], weights=w),
               "mean_km_future": np.average(g["d_future_km"], weights=w)}
        for b in bands:
            row[f"share_within_{b}km_now"] = w[g["d_now_km"] <= b].sum() / w.sum()
            row[f"share_within_{b}km_future"] = w[g["d_future_km"] <= b].sum() / w.sum()
        row[f"people_beyond_{bands[-1]}km_now"] = w[g["d_now_km"] > bands[-1]].sum()
        row[f"people_gaining_{target}km"] = w[(g["d_now_km"] > target) & (g["d_future_km"] <= target)].sum()
        return pd.Series(row)

    by_state = pixels.groupby("state").apply(summarize, include_groups=False)
    by_state.loc["India"] = summarize(pixels)
    return pixels, by_state


# --------------------------------------------------------------------------- density
def density_by_state(access_by_state: pd.DataFrame) -> pd.DataFrame:
    states = load_states()
    area = states.set_index("state").to_crs(EQUAL_AREA).area / 1e6
    df = official().set_index("state")[["length_km"]].rename(columns={"length_km": "official_km"})
    df["area_km2"] = area
    df["population"] = access_by_state["population"]
    df["km_per_1000_km2"] = df["official_km"] / df["area_km2"] * 1000
    df["km_per_lakh_people"] = df["official_km"] / df["population"] * 1e5
    return df.sort_values("km_per_lakh_people")


# --------------------------------------------------------------------------- connectivity
def _graph(name: str = "nh") -> nx.Graph:
    """The `nh` or `road` graph plus gap edges: each dead end joins the nearest other node within graph_snap_m, since
    OSM ways often meet without sharing a node. graph.graph["gap_edges"] counts them."""
    edges = pd.read_parquet(OUT / f"{name}_graph_edges.parquet").sort_values("km", ascending=False)
    graph = nx.Graph()
    graph.add_weighted_edges_from(zip(edges["u"], edges["v"], edges["km"], strict=True), weight="km")
    # parallel edges: the shortest is added last and wins

    nodes = pd.read_parquet(OUT / f"{name}_graph_nodes.parquet").set_index("node_id")
    to_m = pyproj.Transformer.from_crs("EPSG:4326", INDIA_CRS, always_xy=True)
    x, y = to_m.transform(nodes["lon"].values, nodes["lat"].values)
    gaps = gap_edges(graph, pd.DataFrame({"x": x, "y": y}, index=nodes.index), CFG["graph_snap_m"])
    graph.add_weighted_edges_from(zip(gaps["u"], gaps["v"], gaps["km"], strict=True), weight="km")
    graph.graph["gap_edges"] = len(gaps)
    return graph


def gap_edges(graph: nx.Graph, xy: pd.DataFrame, snap_m: float) -> pd.DataFrame:
    """For each dead end (degree 1), an edge (u, v, km) to the nearest node within snap_m that it is
    not already joined to. xy holds metric x, y indexed by node id."""
    pts = shapely.points(xy["x"].values, xy["y"].values)
    ends = np.array([v for v, d in graph.degree() if d == 1])
    if len(ends) == 0:
        return pd.DataFrame(columns=["u", "v", "km"])
    end_pts = pts[xy.index.get_indexer(ends)]
    hit = shapely.STRtree(pts).query(end_pts, predicate="dwithin", distance=snap_m)
    gaps = pd.DataFrame({"u": ends[hit[0]], "v": xy.index.values[hit[1]],
                         "km": shapely.distance(end_pts[hit[0]], pts[hit[1]]) / 1000})
    new = [u != v and not graph.has_edge(u, v) for u, v in zip(gaps["u"], gaps["v"], strict=True)]
    return gaps[new].sort_values("km").drop_duplicates("u").reset_index(drop=True)


def connectivity() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Network islands and city-pair circuity (network km ÷ straight-line km)."""
    graph = _graph()
    nodes = pd.read_parquet(OUT / "nh_graph_nodes.parquet").set_index("node_id")
    comps = sorted(nx.connected_components(graph), key=len, reverse=True)
    comp_rows = []
    for i, comp in enumerate(comps[:15]):
        sub = graph.subgraph(comp)
        xy = nodes.loc[list(comp)]
        comp_rows.append({"component": i, "nodes": len(comp), "km": sub.size(weight="km"),
                          "lon": xy["lon"].mean(), "lat": xy["lat"].mean()})
    islands = pd.DataFrame(comp_rows)
    islands.attrs["n_components"] = len(comps)
    islands.attrs["gap_edges"] = graph.graph["gap_edges"]

    # city pairs route on NH + context roads: NH-only routing breaks where NHs cross cities on roads
    # tagged without an NH ref, which made e.g. Mumbai–Pune look 2.8x the straight line
    graph = _graph("road")
    nodes = pd.read_parquet(OUT / "road_graph_nodes.parquet").set_index("node_id")
    comps = [max(nx.connected_components(graph), key=len)]
    cfg = CFG["city_pairs"]
    cities = load_cities(cfg["min_population"]).head(cfg["top_cities"]).reset_index(drop=True)
    main = nodes.loc[list(comps[0])]
    to_m = pyproj.Transformer.from_crs("EPSG:4326", INDIA_CRS, always_xy=True)
    nx_, ny_ = to_m.transform(main["lon"].values, main["lat"].values)
    tree = shapely.STRtree(shapely.points(nx_, ny_))
    cx, cy = to_m.transform(cities["lon"].values, cities["lat"].values)
    idx, dist = tree.query_nearest(shapely.points(cx, cy), return_distance=True, all_matches=False)
    cities["node"] = main.index.values[idx[1]]
    cities["snap_km"] = dist / 1000
    cities = cities[cities["snap_km"] <= cfg["snap_max_km"]].reset_index(drop=True)
    geod = pyproj.Geod(ellps="WGS84")
    pipe = _pipeline_lines(segments()).to_crs(INDIA_CRS).values
    pipe_tree = shapely.STRtree(pipe)
    rows = []
    for i, a in cities.iterrows():
        lengths = nx.single_source_dijkstra_path_length(graph, a["node"], cutoff=cfg["max_km"] * 3, weight="km")
        for _, b in cities.iloc[i + 1:].iterrows():
            _, _, straight = geod.inv(a["lon"], a["lat"], b["lon"], b["lat"])
            straight /= 1000
            if not cfg["min_km"] <= straight <= cfg["max_km"]:
                continue
            net = lengths.get(b["node"])
            network_km = a["snap_km"] + net + b["snap_km"] if net is not None else np.nan
            corridor = shapely.buffer(shapely.linestrings([[to_m.transform(a["lon"], a["lat"]),
                                                           to_m.transform(b["lon"], b["lat"])]])[0], 10_000)
            rows.append({"city_a": a["name"], "city_b": b["name"], "straight_km": straight,
                         "network_km": network_km, "circuity": network_km / straight,
                         "pipeline_on_route": len(pipe_tree.query(corridor, predicate="intersects")) > 0})
    pairs = pd.DataFrame(rows).sort_values("circuity", ascending=False)
    return islands, pairs


# --------------------------------------------------------------------------- 07 pipeline
def pipeline_by_state() -> tuple[pd.DataFrame, pd.DataFrame]:
    seg = segments()
    osm = seg[seg["status"] != "operational"].pivot_table(
        index="state", columns="status", values="eff_km", aggfunc="sum", fill_value=0).add_prefix("osm_")
    net = nhai_network()
    building = net[net["status"] == "under_construction"]
    nhai = building.pivot_table(index="state", columns="completion", values="length_km",
                                aggfunc="sum", fill_value=0).add_prefix("nhai_target_")
    nhai["nhai_greenfield_km"] = building[building["greenfield"] == "Greenfield"].groupby("state")["length_km"].sum()
    out = osm.join(nhai, how="outer").fillna(0)
    out.loc["India"] = out.sum()
    projects = gpd.read_parquet(OUT / "nhai_projects.parquet")
    projects["length"] = pd.to_numeric(projects["length"], errors="coerce")
    stages = projects.groupby("current_st").agg(projects=("upc", "count"), km=("length", "sum"))
    return out.round(0), stages.sort_values("projects", ascending=False)


# --------------------------------------------------------------------------- 06 safety
def rai_national() -> dict:
    """NH totals quoted from Road Accidents in India 2024: Table 2.5 (2020–24 series) and Table 2.10
    (2024 by road-owning agency). Raises unless both are found and the agencies add up to the total."""
    series, agencies = {}, None
    with pdfplumber.open(RAW / "rai" / "road-accidents-in-india-2024.pdf") as pdf:
        for page in pdf.pages[50:80]:
            text = page.extract_text() or ""
            if "Table 2.5:" in text:
                for year, acc, killed in re.findall(r"^(20[12]\d) ([\d,]+) [-\d.]+ ([\d,]+) ", text, re.MULTILINE):
                    series[year] = {"accidents": parse_indian_number(acc), "deaths": parse_indian_number(killed)}
            if "Table 2.10:" in text and (m := re.search(r"^Total ((?:[\d,]+ ){5}[\d,]+)$", text, re.MULTILINE)):
                n = [parse_indian_number(x) for x in m.group(1).split()]
                agencies = {k: {"accidents": n[2 * i], "deaths": n[2 * i + 1]}
                            for i, k in enumerate(("nhai", "state_pwd", "other"))}
    if "2024" not in series or agencies is None:
        raise ValueError("Road Accidents in India 2024: Table 2.5 or 2.10 not found — layout changed?")
    for key in ("accidents", "deaths"):
        if sum(a[key] for a in agencies.values()) != series["2024"][key]:
            raise ValueError(f"Table 2.10 {key} by agency do not add up to Table 2.5")
    return {"nh_series": series, "by_agency_2024": agencies}


def safety_by_state() -> tuple[pd.DataFrame, pd.DataFrame]:
    crashes = gpd.read_parquet(OUT / "nhai_crashes.parquet")
    crashes = crashes[crashes["date"].dt.year.isin([2022, 2023])]  # full reporting years only
    net = nhai_network().query("status == 'operational' and road_type == 'National Highway'")
    # state rates: Road Accidents in India (all NH crashes, OCR'd annexures checked against totals)
    # over the official NH length; the NHAI layer only adds where its points cluster
    rai = pd.read_csv(OUT / "rai_state_nh.csv")
    latest = rai["year"].max()
    by_state = rai[rai["year"] == latest].set_index("state")[["accidents", "deaths"]]
    first = rai[rai["year"] == rai["year"].min()].set_index("state")["deaths"]
    by_state["official_km"] = official().set_index("state")["length_km"]
    by_state.loc["India"] = by_state.sum()
    first.loc["India"] = first.sum()
    by_state["deaths_per_100km"] = by_state["deaths"] / by_state["official_km"] * 100
    by_state["deaths_change_since_first_year"] = by_state["deaths"] / first - 1
    by_state["nhai_layer_crashes_2022_23"] = crashes.groupby("state").size()
    by_state.loc["India", "nhai_layer_crashes_2022_23"] = len(crashes)
    by_state.attrs["year"] = int(latest)

    # crash density by lane band: snap crashes to the nearest completed NHAI stretch
    lines = net[["lane_statu", "geometry"]].explode(index_parts=False).to_crs(INDIA_CRS).reset_index(drop=True)
    lines["band"] = lines["lane_statu"].map(lane_band)
    pts = crashes.to_crs(INDIA_CRS)
    idx, dist = shapely.STRtree(lines.geometry.values).query_nearest(
        pts.geometry.values, return_distance=True, all_matches=False)
    near = dist <= CFG["crash_snap_m"]
    snapped = pd.DataFrame({"band": lines["band"].values[idx[1][near]],
                            "deaths": pts["deaths"].values[idx[0][near]]})
    band_km = lines.assign(km=geodesic_km(lines.to_crs("EPSG:4326").geometry)).groupby("band")["km"].sum()
    by_band = snapped.groupby("band").agg(crashes=("deaths", "size"), deaths=("deaths", "sum"))
    by_band["km"] = band_km
    by_band["crashes_per_100km_per_year"] = by_band["crashes"] / by_band["km"] * 100 / 2
    by_band["deaths_per_100km_per_year"] = by_band["deaths"] / by_band["km"] * 100 / 2
    by_band.attrs["snapped_share"] = float(near.mean())
    return by_state.sort_values("deaths_per_100km", ascending=False), by_band


# --------------------------------------------------------------------------- 05 corridor effect
def corridor_effect() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Built-up growth 2000→2020 near (0–2 km) vs far (2–10 km) from expressways that opened in
    between, compared with corridors that were not yet open (descriptive difference-in-differences)."""
    seg = segments()
    seg["year"] = seg["opening"].map(parse_year)
    lo, hi = CFG["corridor_open_years"]
    ways = seg[seg["kind"] == "expressway_segment"]
    treated = ways[(ways["status"] == "operational") & ways["year"].between(lo, hi)]
    control = ways[(ways["status"] != "operational") | (ways["year"] > 2020)]
    near_km = CFG["corridor_rings_km"]["near"]
    far_km = CFG["corridor_rings_km"]["far"][1]

    b2000, transform, crs = read_ghsl_built(2000)
    b2020, _, _ = read_ghsl_built(2020)
    rows, cols = np.nonzero((b2000 >= 0) & (b2020 >= 0))
    xs, ys = transform * (cols + 0.5, rows + 0.5)
    to_m = pyproj.Transformer.from_crs(crs, INDIA_CRS, always_xy=True)
    px, py = to_m.transform(xs, ys)
    cells = shapely.points(px, py)
    growth = (b2020[rows, cols] - b2000[rows, cols]) / 1e6 * 100  # percentage points of the 1 km² cell

    def rings(lines: gpd.GeoSeries, label: str) -> pd.DataFrame:
        tree = shapely.STRtree(lines.to_crs(INDIA_CRS).values)
        hit = tree.query(cells, predicate="dwithin", distance=far_km * 1000)
        cand = np.unique(hit[0])
        _, dist = tree.query_nearest(cells[cand], return_distance=True, all_matches=False)
        km = dist / 1000
        ring = np.where(km <= near_km, "near", "far")
        return pd.DataFrame({"group": label, "ring": ring, "growth_pp": growth[cand], "cell": cand})

    frame = pd.concat([rings(treated.geometry, "opened_2001_2019"), rings(control.geometry, "not_yet_open")])
    frame = frame.sort_values("group").drop_duplicates("cell", keep="first")  # a cell counts once
    summary = frame.groupby(["group", "ring"])["growth_pp"].agg(["mean", "median", "count"]).round(3)
    diff = summary["mean"].unstack("ring")
    diff["near_minus_far"] = diff["near"] - diff["far"]
    diff.attrs["did_pp"] = float(diff.loc["opened_2001_2019", "near_minus_far"]
                                 - diff.loc["not_yet_open", "near_minus_far"])
    per_corridor = (treated.assign(corridor=treated["name"].fillna(treated["ref"]).fillna("unnamed"))
                    .groupby("corridor").agg(km=("eff_km", "sum"), opened=("year", "min"))
                    .sort_values("km", ascending=False).head(20))
    return diff, per_corridor


# --------------------------------------------------------------------------- run
def run_all() -> dict:
    A.mkdir(parents=True, exist_ok=True)
    results = {}
    coverage_by_state().to_csv(A / "coverage_by_state.csv", index=False)
    completeness_by_state().to_csv(A / "completeness_by_state.csv")
    lane_mix_by_state().to_csv(A / "lane_mix_by_state.csv")
    toll_coverage_by_state().to_csv(A / "toll_coverage_by_state.csv")
    pixels, acc = access()
    pixels.to_parquet(A / "access_pixels.parquet")
    acc.to_csv(A / "access_by_state.csv")
    density_by_state(acc).to_csv(A / "density_by_state.csv")
    islands, pairs = connectivity()
    islands.to_csv(A / "network_islands.csv", index=False)
    results["n_components"] = islands.attrs["n_components"]
    results["graph_gap_edges"] = islands.attrs["gap_edges"]
    results["city_pairs_over_circuity_flag"] = int((pairs["circuity"] > CFG["circuity_flag"]).sum())
    results["city_pairs"] = len(pairs)
    pairs.to_csv(A / "city_pairs.csv", index=False)
    pipe, stages = pipeline_by_state()
    pipe.to_csv(A / "pipeline_by_state.csv")
    stages.to_csv(A / "nhai_project_stages.csv")
    results["rai_national"] = rai_national()
    safety, by_band = safety_by_state()
    safety.to_csv(A / "safety_by_state.csv")
    by_band.to_csv(A / "crash_rate_by_lane_band.csv")
    results["crash_snapped_share"] = by_band.attrs["snapped_share"]
    diff, per_corridor = corridor_effect()
    diff.to_csv(A / "corridor_effect.csv")
    per_corridor.to_csv(A / "corridor_effect_corridors.csv")
    results["corridor_did_pp"] = diff.attrs["did_pp"]
    (A / "summary.json").write_text(json.dumps(results, indent=2, default=float))
    print(json.dumps(results, indent=2, default=float))
    return results


# --------------------------------------------------------------------------- fixtures
def write_fixtures() -> None:
    """Simplified samples following the shared layer contract (docs/fields/README.md)."""
    seg = segments()
    seg["band"] = [lane_band(n) for n in road_lanes(seg["lanes"], seg["weight"])]
    keys = ["kind", "status", "ref", "band", "owner_level"]
    merged = seg.fillna({"ref": ""}).dissolve(by=keys, as_index=False, aggfunc={"eff_km": "sum"})
    # merge touching way pieces first — simplify cannot thin thousands of two-point parts
    merged["geometry"] = shapely.line_merge(merged.geometry.values)
    merged["geometry"] = merged.geometry.simplify(CFG["fixture_simplify_deg"])
    merged = merged[~merged.geometry.is_empty]
    out = gpd.GeoDataFrame({
        "id": [f"{k}:osm:{r or 'noref'}:{s}:{b}:{o}" for k, s, r, b, o in merged[keys].itertuples(index=False)],
        "field": "national_highways", "kind": merged["kind"], "name": None,
        "ref": merged["ref"].replace("", None), "status": merged["status"], "opened_on": None,
        "expected_completion": None, "agency": None, "source": "osm", "confidence": 0.9,
        "lanes_band": merged["band"], "owner_level": merged["owner_level"],
        "length_km": merged["eff_km"].round(1), "geometry": merged.geometry,
    }, crs="EPSG:4326")
    write_geojson(out, FIXTURES / "nh_segments.geojson")

    plazas = gpd.read_parquet(OUT / "osm_toll_plazas.parquet")
    # a few dozen IHMCL rows carry no code (blank in the source PDF) — never a real match target,
    # and left in they'd collapse to a duplicate-NaN index that pandas refuses to map() against.
    ihmcl = pd.read_csv(OUT / "ihmcl_plazas.csv", dtype={"code": str}).dropna(subset=["code"]).set_index("code")
    code = plazas["ihmcl_code"]
    matched = code.notna()
    write_geojson(gpd.GeoDataFrame({
        "id": [f"toll_plaza:osm:node/{n}" for n in plazas["node_id"]], "field": "national_highways",
        "kind": "toll_plaza",
        "name": np.where(matched, code.map(ihmcl["name"]), plazas["name"]),
        "ref": np.where(matched, "NH" + code.map(ihmcl["nh"]).fillna("").str.extract(r"(\d+[A-Z]*)")[0], None),
        "status": "operational", "opened_on": None, "expected_completion": None,
        "agency": np.where(matched, "NHAI", None), "source": np.where(matched, "osm+ihmcl", "osm"),
        "confidence": np.where(matched, 0.95, 0.8), "ihmcl_code": code, "booths": plazas["booths"],
        "geometry": plazas.geometry.values}, crs="EPSG:4326"), FIXTURES / "toll_plazas.geojson")

    pixels = pd.read_parquet(A / "access_pixels.parquet")
    target = CFG["access_target_km"]
    pixels["h3"] = [h3.latlng_to_cell(lat, lon, CFG["h3_res_fixture"])
                    for lat, lon in zip(pixels["lat"], pixels["lon"], strict=True)]
    hexes = pixels.groupby("h3").apply(lambda g: pd.Series({
        "population": g["pop"].sum(),
        "nh_distance_km": np.average(g["d_now_km"], weights=g["pop"]),
        "nh_distance_km_with_pipeline": np.average(g["d_future_km"], weights=g["pop"]),
        "share_within_10km": g.loc[g["d_now_km"] <= target, "pop"].sum() / g["pop"].sum(),
    }), include_groups=False).reset_index()
    polys = [shapely.Polygon([(lng, lat) for lat, lng in h3.cell_to_boundary(c)]) for c in hexes["h3"]]
    write_geojson(gpd.GeoDataFrame({
        "id": "nh_access:h3:" + hexes["h3"], "field": "national_highways", "kind": "nh_access",
        "source": "osm+worldpop", "confidence": 0.9,
        "population": hexes["population"].round(0),
        "nh_distance_km": hexes["nh_distance_km"].round(2),
        "pipeline_access_gain_km": (hexes["nh_distance_km"] - hexes["nh_distance_km_with_pipeline"]).round(2),
        "share_within_10km": hexes["share_within_10km"].round(3), "geometry": polys}, crs="EPSG:4326"), FIXTURES / "nh_access.geojson")

    cov = pd.read_csv(A / "coverage_by_state.csv").set_index("state")
    acc = pd.read_csv(A / "access_by_state.csv", index_col=0)
    den = pd.read_csv(A / "density_by_state.csv", index_col=0)
    saf = pd.read_csv(A / "safety_by_state.csv", index_col=0)
    pipe = pd.read_csv(A / "pipeline_by_state.csv", index_col=0)
    table = cov[["official_km", "osm_nh_km", "osm_ratio"]].join(
        acc[["population", "mean_km_now", "share_within_10km_now", "share_within_10km_future"]], how="left").join(
        den[["km_per_1000_km2", "km_per_lakh_people"]], how="left").join(
        saf[["accidents", "deaths", "deaths_per_100km"]].add_prefix("rai_2024_"), how="left").join(
        pipe.filter(like="nhai_target_").sum(axis=1).rename("nhai_km_under_construction"), how="left")
    FIXTURES.mkdir(parents=True, exist_ok=True)
    records = json.loads(table.round(3).reset_index().rename(columns={"index": "state"}).to_json(orient="records"))
    (FIXTURES / "nh_state_metrics.json").write_text(json.dumps({
        "field": "national_highways",
        "sources": ["MoRTH Annual Report 2024-25 (Appendix-2, as on 31.12.2024)", "© OpenStreetMap contributors",
                    "WorldPop 2020 1 km", "MoRTH Road Accidents in India 2024 (Annexures 9-10)", "NHAI Datalake (aggregates only, ADR-0014)"],
        "states": records}, indent=1))
    print(f"fixture nh_state_metrics.json: {len(records)} rows")
