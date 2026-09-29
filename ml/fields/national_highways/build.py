"""Build the National Highways field from raw sources (docs/fields/national-highways.md).

Steps — each idempotent, outputs in data/processed/national_highways/ (gitignored):
  extract   OSM PBF -> candidate ways, node sequences, toll booths, NH relations (two DuckDB passes)
  segments  classify and normalize ways -> nh_segments.parquet, ingest_errors.csv
  graph     node sequences -> nh_graph_edges.parquet (junction-to-junction edges in km)
  nhai      NHAI GeoServer layers -> tidy GeoParquet (ADR-0014)
"""

from __future__ import annotations

import json
import shutil

import duckdb
import geopandas as gpd
import numpy as np
import pandas as pd
import pyproj
import shapely
import yaml

from fields.national_highways.normalize import (
    classify_osm,
    dual_carriageway_weights,
    nhai_status,
    parse_indian_number,
    parse_lanes,
    parse_refs,
)
from pipeline.shared_layers import (
    CANONICAL_STATES,
    INDIA_BOUNDS,
    INDIA_CRS,
    PROCESSED,
    RAW,
    ROOT,
    load_states,
    normalize_state,
)

OUT = PROCESSED / "national_highways"
_CFG = yaml.safe_load((ROOT / "config" / "fields" / "national_highways.yaml").read_text())
_GEOD = pyproj.Geod(ellps="WGS84")
_ROAD = "('motorway','trunk','primary','secondary','tertiary')"


def _require(path):
    if not path.exists():
        raise FileNotFoundError(f"{path} missing — run the earlier step or `python -m common.fetch`")
    return path


def geodesic_km(geoms) -> np.ndarray:
    return np.array([_GEOD.geometry_length(g) / 1000 for g in geoms])


def state_at_midpoint(lines: gpd.GeoSeries) -> np.ndarray:
    """State/UT containing each point or line midpoint (nearest within 5 km for coastal/border lines).

    Used for OSM and NHAI alike, so both are split by the same boundaries — NHAI's own state_ut
    field mixes combined names like 'Gujarat, Daman and Diu and Dadra and Nagar Haveli'.
    """
    states = load_states()
    mids = lines if (lines.geom_type == "Point").all() else (
        lines.to_crs(INDIA_CRS).interpolate(0.5, normalized=True).to_crs(lines.crs))
    mids = gpd.GeoDataFrame(geometry=mids.values, crs=lines.crs)
    hit = gpd.sjoin(mids, states, how="left", predicate="within")["state"]
    hit = hit[~hit.index.duplicated()]
    missing = hit.isna()
    if missing.any():
        near = gpd.sjoin_nearest(mids.loc[missing].to_crs(INDIA_CRS), states.to_crs(INDIA_CRS),
                                 how="left", max_distance=5_000)["state"]
        hit.loc[near.index] = near[~near.index.duplicated()]
    return hit.values


# --------------------------------------------------------------------------- extract
def extract_osm() -> None:
    """Three streaming passes over the PBF: (1) IN:NH route relations, (2) candidate ways plus every
    way those relations use, plus context roads for routing, (3) only the nodes those ways use plus
    toll booths. Keeps memory and
    disk low on a laptop."""
    pbf = _require(RAW / "osm" / "india-latest.osm.pbf")
    OUT.mkdir(parents=True, exist_ok=True)
    tmp = OUT / "_duckdb_tmp"
    con = duckdb.connect()
    con.execute("INSTALL spatial; LOAD spatial;")
    con.execute(f"SET temp_directory='{tmp}'; SET memory_limit='10GB'; SET preserve_insertion_order=false")
    con.execute(f"""
        CREATE TABLE rels AS
        SELECT id, tags, refs, ref_types FROM ST_ReadOSM('{pbf}')
        WHERE kind = 'relation' AND tags['network'] = 'IN:NH'
    """)
    con.execute("""CREATE TABLE member_ways AS
                   SELECT DISTINCT id FROM (SELECT unnest(refs) AS id,
                                                   unnest(CAST(ref_types AS VARCHAR[])) AS t FROM rels)
                   WHERE t = 'way'""")
    # relation members catch NH stretches tagged primary/secondary without a ref (city sections)
    field_way = rf"""(
                   tags['highway'] IN ('motorway', 'trunk', 'motorway_link', 'trunk_link')
                OR (tags['highway'] IN ('primary', 'secondary', 'tertiary')
                    AND regexp_matches(coalesce(tags['ref'], ''), '(?i)(^|[;,/ ])(N\.?H|NE)'))
                OR (tags['highway'] IN ('construction', 'proposed')
                    AND coalesce(tags['construction'], tags['proposed']) IN {_ROAD})
                OR (id IN (SELECT id FROM member_ways) AND tags['highway'] IS NOT NULL))"""
    routing = "(" + ", ".join(f"'{c}'" for c in _CFG["routing_road_classes"]) + ")"
    con.execute(f"""
        CREATE TABLE scan AS
        SELECT id, tags, refs, coalesce({field_way}, false) AS is_field
        FROM ST_ReadOSM('{pbf}')
        WHERE kind = 'way' AND ({field_way} OR tags['highway'] IN {routing})
    """)
    con.execute("CREATE TABLE ways AS SELECT id AS way_id, tags, refs FROM scan WHERE is_field")
    # context roads: not part of the field, only used to route city pairs (circuity)
    con.execute("CREATE TABLE ctx_ways AS SELECT id AS way_id, refs FROM scan WHERE NOT is_field")
    con.execute("DROP TABLE scan")
    con.execute("""CREATE TABLE way_nodes AS
                   SELECT way_id, unnest(refs) AS node_id, unnest(generate_series(1, len(refs))) AS pos
                   FROM ways""")
    con.execute("""CREATE TABLE ctx_way_nodes AS
                   SELECT way_id, unnest(refs) AS node_id, unnest(generate_series(1, len(refs))) AS pos
                   FROM ctx_ways""")
    con.execute(f"""
        CREATE TABLE nodes AS
        SELECT id AS node_id, lat, lon, tags
        FROM ST_ReadOSM('{pbf}')
        WHERE kind = 'node' AND (id IN (SELECT node_id FROM way_nodes)
                                 OR id IN (SELECT node_id FROM ctx_way_nodes)
                                 OR tags['barrier'] = 'toll_booth')
    """)
    con.execute(f"""
        COPY (
            WITH lines AS (
                SELECT wn.way_id, count(n.node_id) AS n_nodes,
                       ST_AsWKB(ST_MakeLine(list(ST_Point(n.lon, n.lat) ORDER BY wn.pos)
                                FILTER (WHERE n.node_id IS NOT NULL))) AS wkb
                FROM way_nodes wn LEFT JOIN nodes n USING (node_id)
                GROUP BY wn.way_id
            )
            SELECT w.way_id, to_json(w.tags) AS tags, len(w.refs) AS n_refs, l.n_nodes, l.wkb
            FROM ways w JOIN lines l USING (way_id)
        ) TO '{OUT / "osm_ways.parquet"}' (FORMAT PARQUET)
    """)
    con.execute(f"""
        COPY (SELECT wn.way_id, wn.pos, wn.node_id, n.lon, n.lat
              FROM way_nodes wn JOIN nodes n USING (node_id))
        TO '{OUT / "osm_way_nodes.parquet"}' (FORMAT PARQUET)
    """)
    con.execute(f"""
        COPY (SELECT wn.way_id, wn.pos, wn.node_id, n.lon, n.lat
              FROM ctx_way_nodes wn JOIN nodes n USING (node_id))
        TO '{OUT / "osm_context_way_nodes.parquet"}' (FORMAT PARQUET)
    """)
    con.execute(f"""
        COPY (SELECT node_id, lat, lon, to_json(tags) AS tags FROM nodes WHERE tags['barrier'] = 'toll_booth')
        TO '{OUT / "osm_toll_booths.parquet"}' (FORMAT PARQUET)
    """)
    con.execute(f"""
        COPY (SELECT id AS rel_id, to_json(tags) AS tags, refs, CAST(ref_types AS VARCHAR[]) AS ref_types
              FROM rels)
        TO '{OUT / "osm_nh_relations.parquet"}' (FORMAT PARQUET)
    """)
    counts = {t: con.sql(f"SELECT count(*) FROM {t}").fetchone()[0] for t in ("rels", "member_ways", "ways", "ctx_ways")}
    con.close()
    shutil.rmtree(tmp, ignore_errors=True)
    print(f"extract: {counts}")


# --------------------------------------------------------------------------- segments
def parse_wikipedia_expressway_openings(html_path) -> pd.DataFrame:
    """Named expressways with a reported opening year, from the 'Expressway' + 'Opening' tables on
    Wikipedia's 'Expressways of India' (operational and partially-opened corridors only; OSM rarely
    tags opening_date so this backfills the corridor-effect analysis). Carries provenance per ADR-0012:
    a secondary, community-edited source, so confidence is lower than a primary-agency date."""
    from fields.national_highways.normalize import expressway_key, parse_year

    tables = pd.read_html(html_path)
    rows = []
    for t in tables:
        # tables for under-construction/proposed corridors give a target date and have no Status
        # column at all — skip them so a "planned" date is never mistaken for a real opening.
        if not {"Expressway", "Opening", "Status"} <= set(t.columns):
            continue
        live = t["Status"].astype(str).str.contains("Operational|Partially opened", case=False, na=False)
        for name, opening in zip(t.loc[live, "Expressway"], t.loc[live, "Opening"], strict=True):
            year = parse_year(opening)
            key = expressway_key(name)
            if year and key:
                rows.append({"name": name, "key": key, "opened_year": year})
    df = pd.DataFrame(rows).drop_duplicates("key").assign(
        source="wikipedia_expressways_of_india",
        source_ref="https://en.wikipedia.org/wiki/Expressways_of_India",
        license="CC BY-SA 4.0", confidence=0.7)
    return df.groupby("key", as_index=False).first()


def _relation_refs() -> dict[int, str]:
    """way_id -> NH ref from IN:NH route relations (they carry a bare ref such as '48')."""
    rels = pd.read_parquet(_require(OUT / "osm_nh_relations.parquet"))
    out: dict[int, str] = {}
    for tags_json, members, types in zip(rels["tags"], rels["refs"], rels["ref_types"], strict=True):
        ref = json.loads(tags_json).get("ref", "")
        refs, _ = parse_refs(ref if str(ref).upper().startswith(("NH", "NE")) else f"NH{ref}")
        if not refs:
            continue
        for member, kind in zip(members, types, strict=True):
            if kind == "way":
                out.setdefault(int(member), refs[0])
    return out


def build_segments() -> gpd.GeoDataFrame:
    ways = pd.read_parquet(_require(OUT / "osm_ways.parquet"))
    rel_refs = _relation_refs()
    rows, errors, links = [], [], []
    for way_id, tags_json, n_refs, n_nodes, wkb in ways.itertuples(index=False):
        tags = json.loads(tags_json)
        if tags.get("highway") in ("motorway_link", "trunk_link"):
            links.append(way_id)
            continue
        info = classify_osm(tags)
        ref_source = "way" if info and info["refs"] else None
        if (info is None or not info["refs"]) and way_id in rel_refs:
            # IN:NH route membership supplies the ref when the way carries none (or a non-NH one)
            borrowed = classify_osm({**tags, "ref": rel_refs[way_id]})
            if borrowed is not None:
                borrowed["rejected_refs"] = info["rejected_refs"] if info else []
                info, ref_source = borrowed, "relation"
        if info is None:
            continue
        if n_nodes < max(n_refs, 2) or wkb is None:
            errors.append({"way_id": way_id, "reason": "incomplete_geometry", "value": f"{n_nodes}/{n_refs} nodes"})
            continue
        for token in info["rejected_refs"]:
            errors.append({"way_id": way_id, "reason": "unparsed_ref", "value": token})
        rows.append({
            "way_id": way_id, "kind": info["kind"], "status": info["status"],
            "road_class": info["road_class"], "ref": ";".join(info["refs"]) or None,
            "ref_source": ref_source, "ref_missing": info["ref_missing"],
            "owner_level": info["owner_level"], "lanes": info["lanes"], "oneway": info["oneway"],
            "reversed": info["reversed"], "name": info["name"], "old_ref": info["old_ref"],
            "surface": tags.get("surface"), "maxspeed": tags.get("maxspeed"),
            "opening": tags.get("opening_date") or tags.get("start_date"),
            "geometry": shapely.from_wkb(wkb),
        })
    gdf = gpd.GeoDataFrame(rows, geometry="geometry", crs="EPSG:4326")
    minx, miny, maxx, maxy = INDIA_BOUNDS
    bad = ~gdf.is_valid | ~gdf.geometry.within(shapely.box(minx, miny, maxx, maxy))
    errors += [{"way_id": w, "reason": "invalid_or_outside_india", "value": ""} for w in gdf.loc[bad, "way_id"]]
    gdf = gdf.loc[~bad].reset_index(drop=True)

    gdf["opening_source"] = np.where(gdf["opening"].notna(), "osm", None)
    wiki_path = RAW / "wikipedia" / "expressways_of_india.html"
    if wiki_path.exists():
        from fields.national_highways.normalize import expressway_key

        openings = parse_wikipedia_expressway_openings(wiki_path).set_index("key")["opened_year"]
        missing = (gdf["kind"] == "expressway_segment") & gdf["opening"].isna()
        matched = gdf.loc[missing, "name"].map(expressway_key).map(openings).dropna()
        gdf.loc[matched.index, "opening"] = matched.astype(int).astype(str)
        gdf.loc[matched.index, "opening_source"] = "wikipedia_expressways_of_india"

    gdf["length_km"] = geodesic_km(gdf.geometry)
    metric = gdf.geometry.to_crs(INDIA_CRS)
    gdf["weight"] = dual_carriageway_weights(metric.values, gdf["oneway"].values, gdf["reversed"].values)
    gdf["eff_km"] = gdf["length_km"] * gdf["weight"]

    gdf["state"] = state_at_midpoint(gdf.geometry)
    errors += [{"way_id": w, "reason": "no_state", "value": ""} for w in gdf.loc[gdf["state"].isna(), "way_id"]]

    OUT.mkdir(parents=True, exist_ok=True)
    gdf.to_parquet(OUT / "nh_segments.parquet")
    pd.Series(links, name="way_id").to_frame().to_parquet(OUT / "osm_link_ways.parquet")
    pd.DataFrame(errors, columns=["way_id", "reason", "value"]).to_csv(OUT / "ingest_errors.csv", index=False)
    print(f"segments: {len(gdf):,} ways, {gdf['eff_km'].sum():,.0f} km effective; "
          f"{len(links):,} link ways; {len(errors):,} ingest errors")
    return gdf


# --------------------------------------------------------------------------- graph
def _haversine_km(lon1, lat1, lon2, lat2):
    lon1, lat1, lon2, lat2 = map(np.radians, (lon1, lat1, lon2, lat2))
    a = np.sin((lat2 - lat1) / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2
    return 2 * 6371.0088 * np.arcsin(np.sqrt(a))


def _junction_edges(wn: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Way node sequences -> junction-to-junction edges (u, v, km) and their nodes. A node splits
    ways where it is shared by 2+ ways or ends a way."""
    wn = wn.sort_values(["way_id", "pos"]).reset_index(drop=True)
    same = wn["way_id"].eq(wn["way_id"].shift())
    step = np.where(same, _haversine_km(wn["lon"].shift(), wn["lat"].shift(), wn["lon"], wn["lat"]), 0.0)
    wn["cum_km"] = pd.Series(step).groupby(wn["way_id"]).cumsum()
    uses = wn.groupby("node_id")["way_id"].transform("size")
    first = ~same
    last = ~wn["way_id"].eq(wn["way_id"].shift(-1))
    splits = wn[first | last | (uses >= 2)]
    nxt = splits.groupby("way_id").shift(-1)
    edges = pd.DataFrame({
        "way_id": splits["way_id"], "u": splits["node_id"], "v": nxt["node_id"],
        "km": nxt["cum_km"] - splits["cum_km"],
    }).dropna().astype({"v": "int64"})
    return edges, splits.drop_duplicates("node_id")[["node_id", "lon", "lat"]]


def build_graph() -> pd.DataFrame:
    """Two routable graphs: the operational NH network (links included so grade-separated
    interchanges connect) -> nh_graph_*; the same plus context roads -> road_graph_* for city pairs."""
    seg = pd.read_parquet(_require(OUT / "nh_segments.parquet"), columns=["way_id", "status"])
    links = pd.read_parquet(OUT / "osm_link_ways.parquet")["way_id"]
    keep = pd.Index(seg.loc[seg["status"] == "operational", "way_id"]).union(pd.Index(links))
    wn = pd.read_parquet(_require(OUT / "osm_way_nodes.parquet"))
    wn = wn[wn["way_id"].isin(keep)]
    edges, nodes = _junction_edges(wn)
    edges.to_parquet(OUT / "nh_graph_edges.parquet")
    nodes.to_parquet(OUT / "nh_graph_nodes.parquet")
    print(f"graph: {len(edges):,} edges, {len(nodes):,} junction nodes, {edges['km'].sum():,.0f} km")

    ctx = pd.read_parquet(_require(OUT / "osm_context_way_nodes.parquet"))
    road_edges, road_nodes = _junction_edges(pd.concat([wn, ctx], ignore_index=True))
    road_edges.to_parquet(OUT / "road_graph_edges.parquet")
    road_nodes.to_parquet(OUT / "road_graph_nodes.parquet")
    print(f"road graph: {len(road_edges):,} edges, {len(road_nodes):,} junction nodes")
    return edges


# --------------------------------------------------------------------------- official
def parse_morth_appendix2(pdf_path) -> pd.DataFrame:
    """State-wise NH length, MoRTH Annual Report 2024-25, Appendix-2 (as on 31.12.2024).

    Parsed from word positions: each row's serial number (left column) and length (right column)
    share a baseline; names wrap across columns, so they are fuzzy-matched to canonical names.
    Raises unless every row maps to a distinct state and the rows add up to the printed total.
    """
    import difflib
    import re

    import pdfplumber

    keys = {re.sub(r"[^a-z]", "", s.lower()): s for s in CANONICAL_STATES}
    rows, total = [], None
    with pdfplumber.open(pdf_path) as pdf:
        start = next(i for i, p in enumerate(pdf.pages)
                     if "STATE/UT-WISE DETAILS OF NATIONAL HIGHWAYS" in (p.extract_text() or ""))
        for page in pdf.pages[start:start + 8]:
            if page.page_number > start + 1 and "Appendix-3" in (page.extract_text() or ""):
                break
            width, words = page.width, page.extract_words()
            serials = sorted((w for w in words if w["x0"] < 0.15 * width
                              and re.fullmatch(r"\d{1,2}", w["text"])), key=lambda w: w["top"])
            numbers = [w for w in words if w["x0"] > 0.82 * width and parse_indian_number(w["text"]) is not None]
            counts = [w for w in words if 0.74 * width < w["x0"] < 0.82 * width
                      and re.fullmatch(r"\d{1,3}", w["text"])]
            for i, s in enumerate(serials):
                # names sit vertically centred in merged cells, above and below the serial's line
                upper = (serials[i - 1]["top"] + s["top"]) / 2 if i else s["top"] - 25
                lower = (s["top"] + serials[i + 1]["top"]) / 2 if i + 1 < len(serials) else s["top"] + 25
                length = next((w for w in numbers if abs(w["top"] - s["top"]) <= 3), None)
                count = next((w for w in counts if abs(w["top"] - s["top"]) <= 3), None)
                name = "".join(w["text"] for w in sorted(words, key=lambda w: (w["top"], w["x0"]))
                               if 0.1 * width < w["x0"] < 0.25 * width
                               and upper <= w["top"] < lower and not w["text"].isdigit())
                state = normalize_state(name)
                if state is None:  # wrapped names lose spaces ("HimachPradesh"): fuzzy fallback
                    match = difflib.get_close_matches(re.sub(r"[^a-z]", "", name.lower()), keys, n=1, cutoff=0.6)
                    state = keys[match[0]] if match else None
                if length is None or state is None:
                    raise ValueError(f"Appendix-2 row {s['text']} unreadable (name={name!r})")
                rows.append({"serial": int(s["text"]), "state": state, "name_in_pdf": name,
                             "nh_count": int(count["text"]) if count else None,
                             "length_km": parse_indian_number(length["text"])})
            for w in words:
                if "Total" in (page.extract_text() or "") and w["x0"] > 0.82 * width:
                    value = parse_indian_number(w["text"])
                    if value and value > 100_000:
                        total = value
    df = pd.DataFrame(rows).drop_duplicates("serial").sort_values("serial")
    merged_ut = "Dadra and Nagar Haveli and Daman and Diu"  # listed as two former UTs
    dup = df[df["state"].duplicated(keep=False)]
    if not dup.empty and set(dup["state"]) != {merged_ut}:
        raise ValueError(f"Appendix-2: duplicate states:\n{dup[['serial', 'state', 'name_in_pdf']].to_string(index=False)}")
    df = df.groupby("state", as_index=False, sort=False).agg(
        serial=("serial", "min"), name_in_pdf=("name_in_pdf", " + ".join),
        nh_count=("nh_count", "sum"), length_km=("length_km", "sum"))
    # rows are rounded to whole km, the printed total is not: allow at most 0.5 km per row
    if total is None or abs(df["length_km"].sum() - total) > 0.5 * len(rows):
        raise ValueError(f"Appendix-2: rows sum to {df['length_km'].sum():,} but the printed total is {total}")
    df["printed_total_km"] = total
    df["as_of"] = "2024-12-31"
    df["source"] = "MoRTH Annual Report 2024-25, Appendix-2"
    return df


def build_official() -> pd.DataFrame:
    official = parse_morth_appendix2(_require(RAW / "morth" / "annual-report-2024-25.pdf"))
    official.to_csv(OUT / "official_state_nh_length.csv", index=False)
    print(f"official: {len(official)} states/UTs, {official['length_km'].sum():,} km (as on 31.12.2024)")
    return official


# --------------------------------------------------------------------------- rai (state NH safety)
def _ocr(image, psm: int = 6) -> str:
    """Tesseract on a grayscale PIL image after erasing table gridlines (long dark rows/columns),
    which otherwise wreck the digits. Needs the `tesseract` binary (brew/apt install tesseract)."""
    import subprocess
    import tempfile

    from PIL import Image

    if shutil.which("tesseract") is None:
        raise RuntimeError("tesseract not found — install it (brew install tesseract / apt install tesseract-ocr)")
    a = np.array(image.convert("L"))
    dark = a < 160
    a[dark.mean(axis=1) > 0.4, :] = 255
    a[:, dark.mean(axis=0) > 0.4] = 255
    with tempfile.NamedTemporaryFile(suffix=".png") as f:
        Image.fromarray(a).save(f.name)
        out = subprocess.run(["tesseract", f.name, "-", "--psm", str(psm)], capture_output=True,
                             text=True, check=True, timeout=120)
    return out.stdout


def parse_rai_state_annexures(pdf_path, annexures: dict[str, int]) -> pd.DataFrame:
    """State-wise NH accidents and deaths from Road Accidents in India annexures, which are drawn as
    outlines (no text layer), so they are OCR'd. Raises unless every row maps to a distinct state
    and every year column adds up exactly to the printed Total."""
    import re

    import pdfplumber

    from fields.national_highways.normalize import parse_rai_annexure

    found: dict[str, str] = {}
    with pdfplumber.open(pdf_path) as pdf:
        texts = [page.extract_text() or "" for page in pdf.pages]
        listing = "\n".join(t for t in texts if "List of Annexures" in t)
        # text pages end with their printed page number; annexure pages have no text layer
        numbered = [(i, int(t.strip().splitlines()[-1])) for i, t in enumerate(texts)
                    if t.strip() and t.strip().splitlines()[-1].strip().isdigit()]
        for measure, number in annexures.items():
            m = re.search(rf"^{number}\s.*?(\d{{2,3}})\s*$", listing, re.MULTILINE)
            if not m:
                continue
            printed = int(m.group(1))
            i0, p0 = max(((i, p) for i, p in numbered if p <= printed), key=lambda x: x[1])
            guess = i0 + printed - p0  # blank pages shift this a little, so search around it
            for i in sorted(range(guess - 2, guess + 9), key=lambda j: abs(j - guess)):
                if 0 <= i < len(pdf.pages) and not texts[i].strip():
                    text = _ocr(pdf.pages[i].to_image(resolution=400).original)
                    if re.search(rf"Annexure\s+{number}\b", text[:300]):
                        found[measure] = text
                        break
    missing = set(annexures) - set(found)
    if missing:
        raise ValueError(f"RAI annexures not found: {sorted(missing)}")
    frames = []
    for measure, text in found.items():
        years, rows, totals = parse_rai_annexure(text)
        states = [normalize_state(r["name"]) for r in rows]
        bad = [r["name"] for r, st in zip(rows, states, strict=True) if st is None]
        if bad or len(set(states)) != len(states) or not years:
            raise ValueError(f"RAI {measure}: unmapped or duplicate states {bad}, years {years}")
        values = np.array([r["values"] for r in rows], dtype=object)
        if None in values or totals is None or None in totals or len(totals) != len(years):
            raise ValueError(f"RAI {measure}: unreadable cells or Total row")
        sums = values.astype(int).sum(axis=0).tolist()
        if sums != totals:
            raise ValueError(f"RAI {measure}: columns sum to {sums}, printed Total is {totals}")
        df = pd.DataFrame(values.astype(int), columns=years, index=states)
        frames.append(df.stack().rename(measure))
    out = pd.concat(frames, axis=1).rename_axis(["state", "year"]).reset_index()
    return out


def build_rai() -> pd.DataFrame:
    rai = parse_rai_state_annexures(_require(RAW / "rai" / "road-accidents-in-india-2024.pdf"),
                                    {"accidents": 9, "deaths": 10})
    rai.to_csv(OUT / "rai_state_nh.csv", index=False)
    latest = rai[rai["year"] == rai["year"].max()]
    print(f"rai: {rai['state'].nunique()} states, {rai['year'].min()}–{rai['year'].max()}; "
          f"{latest['year'].iloc[0]}: {latest['accidents'].sum():,} accidents, {latest['deaths'].sum():,} deaths")
    return rai


# --------------------------------------------------------------------------- toll plazas
def parse_ihmcl_plazas(pdf_path) -> pd.DataFrame:
    """IHMCL 'NH Fee Plazas' list: code, name, state, district, section, NH (no coordinates).
    Raises unless serial numbers run 1..n without gaps and every state is recognized."""
    import pdfplumber

    rows = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            for table in page.extract_tables():
                rows += [r[:7] for r in table if r and r[0] and r[0].strip().isdigit()]
    df = pd.DataFrame(rows, columns=["serial", "code", "name", "state_raw", "district", "section", "nh"])
    serial = df["serial"].astype(int)
    if serial.tolist() != list(range(1, len(df) + 1)):
        raise ValueError("IHMCL list: serial numbers are not contiguous — table parse broke")
    df["state"] = df["state_raw"].map(normalize_state)
    if df["state"].isna().any():
        raise ValueError(f"IHMCL list: unknown states {sorted(df.loc[df['state'].isna(), 'state_raw'].unique())}")
    return df.drop(columns="serial")


def build_tolls() -> pd.DataFrame:
    """Cluster OSM toll booths near NH ways into plazas and match them to the IHMCL list by name
    within the same state (names only — IHMCL gives no coordinates)."""
    import networkx as nx

    from fields.national_highways.normalize import plaza_key, plaza_name_score

    ihmcl = parse_ihmcl_plazas(_require(RAW / "ihmcl" / "nh-fee-plazas.pdf"))
    booths = pd.read_parquet(_require(OUT / "osm_toll_booths.parquet"))
    pts = gpd.GeoDataFrame(booths, geometry=gpd.points_from_xy(booths["lon"], booths["lat"]),
                           crs="EPSG:4326").to_crs(INDIA_CRS)
    seg = gpd.read_parquet(_require(OUT / "nh_segments.parquet"), columns=["geometry"]).to_crs(INDIA_CRS)
    near = shapely.STRtree(seg.geometry.values).query(pts.geometry.values, predicate="dwithin",
                                                      distance=_CFG["toll_booth_snap_m"])
    pts = pts.iloc[np.unique(near[0])].reset_index(drop=True)
    pairs = shapely.STRtree(pts.geometry.values).query(pts.geometry.values, predicate="dwithin",
                                                       distance=_CFG["toll_cluster_m"])
    g = nx.Graph()
    g.add_nodes_from(range(len(pts)))
    g.add_edges_from(zip(pairs[0], pairs[1], strict=True))
    pts["plaza"] = 0
    for k, comp in enumerate(nx.connected_components(g)):
        pts.loc[list(comp), "plaza"] = k
    pts["name"] = [json.loads(t).get("name") for t in pts["tags"]]
    plazas = pts.dissolve(by="plaza", aggfunc={"node_id": "first", "name": "first"}).centroid.to_frame("geometry")
    plazas = gpd.GeoDataFrame(plazas, crs=INDIA_CRS).join(
        pts.groupby("plaza").agg(node_id=("node_id", "min"), booths=("node_id", "size"),
                                 name=("name", lambda s: s.dropna().iloc[0] if s.notna().any() else None)))
    plazas = plazas.to_crs("EPSG:4326").reset_index()
    plazas["state"] = state_at_midpoint(plazas.geometry)

    ihmcl["key"] = ihmcl["name"].map(plaza_key)
    plazas["key"] = plazas["name"].map(plaza_key)
    plazas["ihmcl_code"] = None
    taken: set[str] = set()
    for i, row in plazas[plazas["key"] != ""].iterrows():
        cand = ihmcl[(ihmcl["state"] == row["state"]) & ~ihmcl["code"].isin(taken)]
        best = max(((plaza_name_score(row["key"], k), c) for k, c in zip(cand["key"], cand["code"], strict=True)),
                   default=(0.0, None))
        if best[0] >= _CFG["toll_name_match"]:
            plazas.at[i, "ihmcl_code"] = best[1]
            taken.add(best[1])
    ihmcl.to_csv(OUT / "ihmcl_plazas.csv", index=False)
    plazas.to_parquet(OUT / "osm_toll_plazas.parquet")
    print(f"tolls: IHMCL {len(ihmcl):,} plazas; OSM {len(plazas):,} plazas from {len(pts):,} booths; "
          f"{plazas['ihmcl_code'].notna().sum():,} matched by name")
    return plazas


# --------------------------------------------------------------------------- nhai
def build_nhai() -> None:
    """Tidy the NHAI layers fetched with keep-lists (ADR-0014). Unrecognized values are counted,
    not guessed."""
    src = RAW / "nhai"
    net = gpd.read_file(_require(src / "nh_network_of_india_new.geojson"))
    net["status"] = net["completion"].map(nhai_status)
    net["lanes"] = net["lane_statu"].map(parse_lanes)
    net["state"] = state_at_midpoint(net.geometry)
    net["length_km"] = geodesic_km(net.geometry)
    unknown = {c: sorted(net.loc[net[c].isna() & net[s].notna(), s].astype(str).unique())[:20]
               for c, s in (("status", "completion"), ("lanes", "lane_statu"))}
    unknown["state"] = int(net["state"].isna().sum())
    net.to_parquet(OUT / "nhai_network.parquet")

    tolls = gpd.read_file(_require(src / "toll_plaza.geojson"))
    tolls["lanes"] = tolls["nooflanes"].map(parse_lanes)
    tolls.to_parquet(OUT / "nhai_toll_plazas.parquet")

    crashes = gpd.read_file(_require(src / "road_accident_spots.geojson"))
    crashes["date"] = pd.to_datetime(crashes["accident_d"].astype(str).str.rstrip("Z"), errors="coerce")
    crashes["deaths"] = pd.to_numeric(crashes["no__of_fat"], errors="coerce")
    states = load_states()
    crashes = gpd.sjoin(crashes, states, how="left", predicate="within").drop(columns="index_right")
    crashes.to_parquet(OUT / "nhai_crashes.parquet")

    spots = gpd.read_file(_require(src / "black_spots.geojson"))
    spots["state_norm"] = spots["state"].map(normalize_state)
    spots.to_parquet(OUT / "nhai_black_spots.parquet")

    projects = gpd.read_file(_require(src / "upc_projects.geojson"))
    projects.to_parquet(OUT / "nhai_projects.parquet")
    corridors = gpd.read_file(_require(src / "bharatmala_corridors.geojson"))
    corridors["length_km"] = geodesic_km(corridors.geometry)
    corridors.to_parquet(OUT / "nhai_bharatmala.parquet")
    print(f"nhai: network {len(net):,}, tolls {len(tolls):,}, crashes {len(crashes):,}, "
          f"black spots {len(spots):,}, projects {len(projects):,}, corridors {len(corridors):,}")
    print(f"nhai unrecognized values (left as null): {unknown}")
