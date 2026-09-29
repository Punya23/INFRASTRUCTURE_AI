"""Fixture export (spec §6): scored cities and H3 areas become the tree the Go API serves.

`write_fixtures` scores every cell once (a cell shared by two cities has one set of scores),
aggregates each city, and writes meta.json, states.json, cities.json, areas/<id>.geojson.gz and
assets/<id>.json.gz. Besides its arguments it reads only config/states.yaml and
config/sources.yaml. Output is deterministic (sorted keys and rows, gzip mtime 0), and the new tree
replaces the old one only after every file is built and fits the size budget.
"""

from __future__ import annotations

import gzip
import json
import math
import shutil
from collections import Counter
from pathlib import Path

import h3
import numpy as np
import pandas as pd
import yaml

from pipeline.invest.scores import (
    ROOT,
    AreaScore,
    ScoringConfig,
    aggregate_city,
    score_area,
    subscore,
)

STATES_PATH = ROOT / "config" / "states.yaml"
SOURCES_PATH = ROOT / "config" / "sources.yaml"
SCHEMA_VERSION = 1
DISCLAIMER = (
    "Scores describe existing infrastructure and past growth. "
    "They are not forecasts, price predictions or financial advice."
)
OSM = "osm_india"  # config/sources.yaml id of the OSM extract
# Registry ids every city and area is built from (OSM first, so its share-alike license leads);
# the transit feeds a city also draws on come from its assets.
BASE_SOURCES = (
    OSM,
    "worldpop_india_2020_1km",
    "ghsl_built_s_2000_1km",
    "ghsl_built_s_2020_1km",
    "geonames_cities15000",
    "datameet_states",
)
AREA_TAG, ASSET_TAG, TRANSIT_TAG = "osm+worldpop2020+ghsl2020", "osm", "+gtfs"  # spec §6
_CELL_COLUMNS = {"cell", "lat", "lon", "pop", "name", "bus_stops"}
_CITY_COLUMNS = {"id", "name", "state", "aliases", "lat", "lon", "population", "tier"}
_BUS_SOURCE_FIELDS = ("operator", "tier", "license", "fetched_at")  # what the file shows
_BLOCK = 4096  # bytes; a file takes whole 4 KiB blocks on disk (APFS and ext4 defaults)


def _r(x: float | None, digits: int) -> float | None:
    """Rounded for the fixtures; None and NaN (unobserved) stay None, and -0.0 becomes 0.0."""
    return None if x is None or math.isnan(x) else round(float(x), digits) + 0.0


def _json(obj: object) -> bytes:
    return json.dumps(
        obj, sort_keys=True, ensure_ascii=False, allow_nan=False, separators=(",", ":")
    ).encode()


def _gz(obj: object) -> bytes:
    return gzip.compress(_json(obj), compresslevel=9, mtime=0)


def _rows(records: list[dict]) -> bytes:
    """A JSON array with one record per line: same bytes as compact JSON plus newlines, and a
    re-run shows up in git as a per-record diff."""
    return b"[\n" + b",\n".join(_json(r) for r in records) + b"\n]\n"


def _check_inputs(
    cfg: ScoringConfig,
    cities: pd.DataFrame,
    cells: pd.DataFrame,
    memberships: pd.DataFrame,
    assets: dict[str, dict],
    state_codes: set[str],
) -> None:
    """Fail closed (AGENTS invariant 2) on anything the API would refuse or silently misread."""
    for what, frame, cols in (
        ("cities", cities, _CITY_COLUMNS),
        ("cells", cells, _CELL_COLUMNS | set(cfg.factors)),
        ("memberships", memberships, {"city_id", "cell"}),
    ):
        if missing := cols - set(frame.columns):
            raise ValueError(f"{what}: missing columns {sorted(missing)}")
    problems = {
        "duplicate city ids": sorted(cities.loc[cities["id"].duplicated(), "id"]),
        "duplicate cells": sorted(cells.loc[cells["cell"].duplicated(), "cell"]),
        "unknown state codes": sorted(set(cities["state"]) - state_codes),
        "memberships of unknown cities": sorted(set(memberships["city_id"]) - set(cities["id"])),
        "member cells without facts": sorted(set(memberships["cell"]) - set(cells["cell"])),
        "cities without cells": sorted(set(cities["id"]) - set(memberships["city_id"])),
        "cities without assets": sorted(set(cities["id"]) - set(assets)),
    }
    pop = cells["pop"].to_numpy(dtype=float, na_value=np.nan)
    low = ~(pop >= cfg.raw["grid"]["min_area_population"])  # NaN counts as too low
    problems["cells below min_area_population"] = sorted(cells.loc[low, "cell"])
    for city_id, a in assets.items():
        if (a["bus_stops"] is None) != (a["bus_source"] is None):
            problems.setdefault("bus_stops without bus_source (or back)", []).append(city_id)
        if any(p["mode"] not in ("metro", "rail") for _, _, p in a["stations"]):
            problems.setdefault("stations of unknown mode", []).append(city_id)
    found = {k: v[:5] for k, v in problems.items() if v}
    if found:
        raise ValueError(f"write_fixtures inputs rejected: {found}")


def _score_cells(cfg: ScoringConfig, cells: pd.DataFrame) -> dict[str, dict]:
    """Per cell id: raw values, sub-scores and one AreaScore per preset (config order).

    Raw value -> subscore() -> score_area(), never a raw pandas value straight into score_area.
    A cell none of whose weighted factors was observed has no honest score and stops the run.
    """
    raw = {f: cells[f].to_numpy(dtype=float, na_value=np.nan) for f in cfg.factors}
    out = {}
    for i, cell in enumerate(cells.index):
        values = {f: float(raw[f][i]) for f in cfg.factors}
        subs = {f: subscore(factor, values[f]) for f, factor in cfg.factors.items()}
        by_preset = {pid: score_area(cfg, pid, subs) for pid in cfg.presets}
        if missing := [pid for pid, a in by_preset.items() if a is None]:
            raise ValueError(f"cell {cell}: no factor weighted by presets {missing} was observed")
        out[cell] = {"raw": values, "subs": subs, "scores": by_preset}
    return out


def _area_props(cell: str, row: pd.Series, s: dict, default: str) -> dict:
    """A cell's feature properties except `elig`, which depends on the city (spec §4)."""
    scores: dict[str, AreaScore] = s["scores"]
    bus = float(row["bus_stops"])
    return {
        "id": cell,
        "name": None if pd.isna(row["name"]) else str(row["name"]),
        "pop": round(row["pop"]),
        "bus_stops": None if math.isnan(bus) else round(bus),
        "f": {f: _r(v, 1) for f, v in s["raw"].items()},
        "s": {f: _r(v, 1) for f, v in s["subs"].items()},
        "sc": {pid: _r(a.score, 1) for pid, a in scores.items()},
        "ac": {pid: _r(a.access, 1) for pid, a in scores.items()},
        "d": {pid: [[f, _r(p, 1)] for f, p in a.drivers] for pid, a in scores.items()},
        "g": {pid: [[f, _r(v, 1)] for f, v in a.gaps] for pid, a in scores.items()},
        "cov": _r(scores[default].coverage, 2),  # one value per cell: the default preset's
        "conf": _r(scores[default].confidence, 2),
        "source_ref": f"h3:{cell}",
    }


def _polygon(cell: str) -> dict:
    """The cell's hexagon: [lon, lat] to 4 decimals, counter-clockwise, closed."""
    ring = [[_r(lng, 4), _r(lat, 4)] for lat, lng in h3.cell_to_boundary(cell)]
    return {"type": "Polygon", "coordinates": [[*ring, ring[0]]]}


def weighted_median(values: np.ndarray, weights: np.ndarray) -> float:
    """Lower weighted median: the smallest value whose cumulative weight reaches half the total,
    so it is always an observed value, never an interpolation."""
    order = np.argsort(values, kind="stable")
    cumulative = np.cumsum(weights[order])
    return float(values[order][np.searchsorted(cumulative, cumulative[-1] / 2)])


def _factor_summary(
    cfg: ScoringConfig, frame: pd.DataFrame, pops: np.ndarray, subscores: dict
) -> dict[str, dict]:
    """City summary per factor (spec §4): population-weighted median raw value, share of residents
    within the headline band, and the city sub-score. Only cells where the factor was observed
    count; a factor observed nowhere is null throughout, never 0."""
    out = {}
    for f, factor in cfg.factors.items():
        values = frame[f].to_numpy(dtype=float, na_value=np.nan)
        seen = ~np.isnan(values)
        band = factor.headline_band_km
        value = share = None
        if seen.any():
            value = weighted_median(values[seen], pops[seen])
            if band is not None:
                share = pops[seen][values[seen] <= band].sum() / pops[seen].sum()
        out[f] = {
            "value": _r(value, 1),
            "unit": factor.unit,
            "share": _r(share, 2),
            "band_km": band,
            "subscore": _r(subscores[f], 1),
        }
    return out


def _city_scores(
    agg: AreaScore, summary: dict, best: str, best_score: float, best_name: str | None
) -> dict:
    def context(f: str) -> dict:
        return {k: summary[f][k] for k in ("value", "unit", "share", "band_km")}

    return {
        "score": _r(agg.score, 1),
        "access": _r(agg.access, 1),
        "momentum": _r(agg.momentum, 1),
        "coverage": _r(agg.coverage, 2),
        "confidence": _r(agg.confidence, 2),
        "drivers": [{"factor": f, "points": _r(p, 1), **context(f)} for f, p in agg.drivers],
        "gaps": [{"factor": f, "subscore": _r(v, 1), **context(f)} for f, v in agg.gaps],
        "best_area": {"id": best, "name": best_name, "score": _r(best_score, 1)},
    }


def _points(items: list) -> dict:
    features = [
        {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [_r(lon, 4), _r(lat, 4)]},
            "properties": dict(props),
        }
        for lon, lat, props in items
    ]
    return {"type": "FeatureCollection", "features": sorted(features, key=_json)}


def _lines(items: list) -> dict:
    features = []
    for lines, props in items:
        coords = [[[_r(lon, 4), _r(lat, 4)] for lon, lat in line] for line in lines]
        geometry = (
            {"type": "LineString", "coordinates": coords[0]}
            if len(coords) == 1
            else {"type": "MultiLineString", "coordinates": coords}
        )
        features.append({"type": "Feature", "geometry": geometry, "properties": dict(props)})
    return {"type": "FeatureCollection", "features": sorted(features, key=_json)}


def _transit_feeds(a: dict) -> set[str]:
    """Registry ids of the non-OSM (GTFS) feeds whose stations or stops a city's files carry."""
    feeds = {p["source"] for _, _, p in a["stations"]} - {OSM}
    return feeds | ({a["bus_source"]["source"]} if a["bus_source"] else set())


def _license(registry: dict, ids: list[str]) -> str:
    """The distinct licenses of `ids`, in the given order, as one string."""
    return "; ".join(dict.fromkeys(registry[i]["license"] for i in ids))


def _source_entry(registry: dict, source_id: str) -> dict:
    if source_id not in registry:
        raise ValueError(f"source {source_id!r} is not registered in {SOURCES_PATH}")
    entry = registry[source_id]
    return {
        "id": source_id,
        "name": entry["attribution"].split(" — ")[0],  # the provider, before the description
        "license": entry["license"],
        "attribution": entry["attribution"],
    }


def _publish(out_dir: Path, files: dict[str, bytes], max_file: float, max_dir: float) -> None:
    """Write `files` to a temp directory, then swap it in for `out_dir`. The size budget is
    checked first, so a tree that does not fit never replaces the old one."""
    too_big = {p: len(b) for p, b in files.items() if len(b) > max_file}
    if too_big:
        raise ValueError(f"fixture files over {max_file:,.0f} bytes: {too_big}")
    on_disk = sum(-(-len(b) // _BLOCK) * _BLOCK for b in files.values())
    if on_disk > max_dir:
        raise ValueError(f"fixtures take {on_disk:,} bytes on disk, over {max_dir:,.0f}")
    tmp, old = (out_dir.with_name(f".{out_dir.name}.{s}") for s in ("tmp", "old"))
    for d in (tmp, old):
        shutil.rmtree(d, ignore_errors=True)
    for rel, data in sorted(files.items()):
        path = tmp / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    if out_dir.exists():
        out_dir.rename(old)
    tmp.rename(out_dir)
    shutil.rmtree(old, ignore_errors=True)


def write_fixtures(
    out_dir: Path,
    cfg: ScoringConfig,
    cities: pd.DataFrame,
    cells: pd.DataFrame,
    memberships: pd.DataFrame,
    assets: dict[str, dict],
    as_of: str,
) -> None:
    """Score, aggregate and write the fixture tree of spec §6 into `out_dir` (replacing it).

    cities: id, name, state (ISO code), aliases (list), lat, lon, population, tier.
    cells: cell, lat, lon, pop, name (str or None), bus_stops (float; NaN = no feed) and one raw
        value column per factor (NaN = unobserved).
    memberships: city_id, cell; a cell may belong to several cities.
    assets[city_id]: {"stations": [(lon, lat, {name, mode, source})], "bus_stops": None or
        [(lon, lat, {name})], "bus_source": None or {source, operator, tier, license,
        fetched_at}, "highways": [(lines, {ref, status, kind})], "toll_plazas": [(lon, lat,
        {name})]} where `lines` is a list of [(lon, lat), ...] and every `source` is a
        config/sources.yaml id. bus_source["source"] feeds meta.json and is not written itself.
    Raises ValueError, before anything is written, on inputs the API would reject.
    """
    registry = yaml.safe_load(SOURCES_PATH.read_text())
    states = yaml.safe_load(STATES_PATH.read_text())["states"]
    _check_inputs(cfg, cities, cells, memberships, assets, {s["code"] for s in states})
    default = next(p.id for p in cfg.presets.values() if p.default)
    best_min = cfg.raw["grid"]["best_area_min_population"]
    cells = cells.set_index("cell")
    scored = _score_cells(cfg, cells)
    props = {c: _area_props(c, row, scored[c], default) for c, row in cells.iterrows()}
    members = memberships.groupby("city_id")["cell"].agg(lambda s: sorted(set(s)))

    files: dict[str, bytes] = {}
    records, used = [], set(BASE_SOURCES)
    for city in cities.sort_values(["population", "id"], ascending=[False, True]).itertuples():
        ids, a = members[city.id], assets[city.id]
        feeds = sorted(_transit_feeds(a))
        used.update(feeds)
        tag = TRANSIT_TAG if feeds else ""
        pops = np.array([props[c]["pop"] for c in ids], dtype=float)
        elig = pops >= best_min
        if elig.sum() < 3:  # a small city still names its best areas (spec §4)
            elig[:] = True
        aggs = {
            pid: aggregate_city(cfg, pid, [scored[c]["scores"][pid] for c in ids], list(pops))
            for pid in cfg.presets
        }
        if missing := [p for p, g in aggs.items() if g.access is None or g.momentum is None]:
            raise ValueError(f"city {city.id}: no access or momentum under presets {missing}")
        summary = _factor_summary(cfg, cells.loc[ids], pops, aggs[default].subscores)
        eligible = [c for c, e in zip(ids, elig, strict=True) if e]
        scores = {}
        for pid, agg in aggs.items():
            best = min(eligible, key=lambda c: (-scored[c]["scores"][pid].score, c))
            best_score = scored[best]["scores"][pid].score
            scores[pid] = _city_scores(agg, summary, best, best_score, props[best]["name"])
        license = _license(registry, [*BASE_SOURCES, *feeds])
        order = sorted(
            range(len(ids)), key=lambda i: (-scored[ids[i]]["scores"][default].score, ids[i])
        )
        files[f"areas/{city.id}.geojson.gz"] = _gz(
            {
                "type": "FeatureCollection",
                "city": city.id,
                "source": AREA_TAG + tag,
                "fetched_at": as_of,
                "license": license,
                "features": [
                    {
                        "type": "Feature",
                        "geometry": _polygon(ids[i]),
                        "properties": {**props[ids[i]], "elig": bool(elig[i])},
                    }
                    for i in order
                ],
            }
        )
        bus = a["bus_source"]
        files[f"assets/{city.id}.json.gz"] = _gz(
            {
                "city": city.id,
                "source": ASSET_TAG + tag,
                "fetched_at": as_of,
                "license": _license(registry, [OSM, *feeds]),
                "stations": _points(a["stations"]),
                "bus_stops": None if bus is None else _points(a["bus_stops"]),
                "bus_source": None if bus is None else {k: bus[k] for k in _BUS_SOURCE_FIELDS},
                "highways": _lines(a["highways"]),
                "toll_plazas": _points(a["toll_plazas"]),
            }
        )
        modes = Counter(p["mode"] for _, _, p in a["stations"])
        records.append(
            {
                "id": city.id,
                "name": city.name,
                "state": city.state,
                "aliases": [str(x) for x in city.aliases],
                "lat": _r(city.lat, 4),
                "lon": _r(city.lon, 4),
                "population": round(city.population),
                "area_km2": _r(sum(h3.cell_area(c, "km^2") for c in ids), 1),
                "tier": city.tier,
                "cells": len(ids),
                "factors": summary,
                "scores": scores,
                "data": {
                    "bus": None
                    if bus is None
                    else {
                        "operator": bus["operator"],
                        "tier": bus["tier"],
                        "stops": len(a["bus_stops"]),
                    },
                    "metro_stations": modes["metro"],
                    "rail_stations": modes["rail"],
                },
                "source": AREA_TAG + tag,
                "source_ref": f"city:{city.id}",
                "fetched_at": as_of,
                "license": license,
                "confidence": scores[default]["confidence"],
            }
        )

    counts = Counter(r["state"] for r in records)
    files["states.json"] = _rows(
        [{"code": s["code"], "name": s["name"], "city_count": counts[s["code"]]} for s in states]
    )
    files["cities.json"] = _rows(records)
    meta = {
        "schema_version": SCHEMA_VERSION,
        "as_of": as_of,
        "grid": cfg.raw["grid"],
        "factors": [
            {
                "id": f.id,
                "group": f.group,
                "unit": f.unit,
                "better": f.better,
                "headline_band_km": f.headline_band_km,
                "bands": [list(b) for b in f.bands],
            }
            for f in cfg.factors.values()
        ],
        "presets": [
            {"id": p.id, "weights": p.weights, "default": p.default} for p in cfg.presets.values()
        ],
        "tiers": cfg.raw["cities"]["tiers"],
        "sources": [_source_entry(registry, s) for s in sorted(used)],
        "disclaimer": DISCLAIMER,
    }
    files["meta.json"] = (
        json.dumps(meta, sort_keys=True, ensure_ascii=False, allow_nan=False, indent=2) + "\n"
    ).encode()
    budget = cfg.raw["pipeline"]
    _publish(out_dir, files, budget["max_file_mb"] * 1e6, budget["max_dir_mb"] * 1e6)
