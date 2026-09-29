import gzip
import json
from itertools import pairwise

import h3
import numpy as np
import pandas as pd
import pytest

from pipeline.invest.export import weighted_median, write_fixtures
from pipeline.invest.scores import load_config


@pytest.fixture
def synthetic_world():
    cfg = load_config()
    ids = [h3.latlng_to_cell(18.50 + 0.03 * i, 73.80, 7) for i in range(5)]
    latlon = [h3.cell_to_latlng(c) for c in ids]
    cities = pd.DataFrame(
        [
            {"id": "alpha", "name": "Alpha", "state": "MH", "aliases": ["Alpha East"], "lat": 18.5, "lon": 73.8,
             "population": 300000.0, "tier": "mid", "geonameid": 1},
            {"id": "beta", "name": "Beta", "state": "MH", "aliases": [], "lat": 18.6, "lon": 73.9,
             "population": 200000.0, "tier": "mid", "geonameid": 2},
        ]
    )
    cells = pd.DataFrame(
        {
            "cell": ids,
            "lat": [p[0] for p in latlon],
            "lon": [p[1] for p in latlon],
            "pop": [9000.0, 6000.0, 1200.0, 8000.0, 5200.0],
            "name": ["Baner", None, "Pashan", "Wakad", "Aundh"],
            "bus_stops": [4.0, np.nan, np.nan, 2.0, 0.0],
            "nh_access": [1.0, 4.0, 30.0, 2.0, 9.0],
            "rail_access": [3.0, 8.0, 20.0, np.nan, 1.0],  # unobserved in one cell
            "metro_access": [40.0, 40.0, 40.0, 5.0, 0.5],
            "road_strength": [2.0, 1.0, 0.1, 1.5, 2.5],
            "built_up_growth": [30.0, 12.0, 2.0, 25.0, 6.0],
        }
    )
    memberships = pd.DataFrame(
        {"city_id": ["alpha"] * 3 + ["beta"] * 3, "cell": [ids[0], ids[1], ids[2], ids[2], ids[3], ids[4]]}
    )  # ids[2] belongs to both cities
    empty = {"stations": [], "bus_stops": None, "bus_source": None, "highways": [], "toll_plazas": []}
    return cfg, cities, cells, memberships, {"alpha": dict(empty), "beta": dict(empty)}


def test_export_is_valid_deterministic_and_provenanced(tmp_path, synthetic_world):
    cfg, cities, cells, memberships, assets = synthetic_world
    write_fixtures(tmp_path / "a", cfg, cities, cells, memberships, assets, "2026-09-29")
    write_fixtures(tmp_path / "b", cfg, cities, cells, memberships, assets, "2026-09-29")
    for f in sorted((tmp_path / "a").rglob("*")):
        if f.is_file():
            assert f.read_bytes() == (tmp_path / "b" / f.relative_to(tmp_path / "a")).read_bytes()
    city = json.loads((tmp_path / "a" / "cities.json").read_text())[0]
    for key in ("source", "source_ref", "fetched_at", "license", "confidence"):
        assert city[key] not in (None, "")
    area = json.loads(gzip.decompress(next((tmp_path / "a" / "areas").glob("*.gz")).read_bytes()))
    assert {"source", "fetched_at", "license"} <= set(area)
    for feat in area["features"]:
        p = feat["properties"]
        assert set(p["f"]) == set(p["s"]) == set(cfg.factors)
        for preset, weights in ((pid, pr.weights) for pid, pr in cfg.presets.items()):
            obs = {f: p["s"][f] for f in p["s"] if p["s"][f] is not None and weights[f] > 0}
            expected = sum(weights[f] * s for f, s in obs.items()) / sum(weights[f] for f in obs)
            assert abs(p["sc"][preset] - expected) <= 0.15  # the parity rule the Go store re-checks

def test_a_cell_shared_by_two_cities_has_identical_scores(tmp_path, synthetic_world):
    cfg, cities, cells, memberships, assets = synthetic_world
    write_fixtures(tmp_path, cfg, cities, cells, memberships, assets, "2026-09-29")

    def features(city):
        raw = gzip.decompress((tmp_path / "areas" / f"{city}.geojson.gz").read_bytes())
        return {f["properties"]["id"]: f["properties"] for f in json.loads(raw)["features"]}

    a, b = features("alpha"), features("beta")
    (cell,) = set(a) & set(b)
    assert a[cell]["sc"] == b[cell]["sc"] and a[cell]["s"] == b[cell]["s"]


def test_unobserved_factor_is_null_and_lowers_coverage_never_zero(tmp_path, synthetic_world):
    cfg, cities, cells, memberships, assets = synthetic_world
    write_fixtures(tmp_path, cfg, cities, cells, memberships, assets, "2026-09-29")
    raw = gzip.decompress((tmp_path / "areas" / "beta.geojson.gz").read_bytes())
    unobserved = [f["properties"] for f in json.loads(raw)["features"] if f["properties"]["f"]["rail_access"] is None]
    assert unobserved and all(p["s"]["rail_access"] is None and p["cov"] < 1 for p in unobserved)


# --- beyond the brief: what the Go store re-checks, and the export's own promises ---------------


def _read(root, rel):
    data = (root / rel).read_bytes()
    return json.loads(gzip.decompress(data) if rel.endswith(".gz") else data)


def _world_with_assets(synthetic_world):
    """Alpha gets two stations (one from a GTFS feed), a bus feed, a highway and a toll plaza."""
    cfg, cities, cells, memberships, assets = synthetic_world
    assets["alpha"] = {
        "stations": [
            (73.80, 18.50, {"name": "Alpha Metro", "mode": "metro", "source": "gtfs_bengaluru_bmrcl"}),
            (73.81, 18.51, {"name": None, "mode": "rail", "source": "osm_india"}),
        ],
        "bus_stops": [(73.8, 18.5, {"name": "Stop A"}), (73.9, 18.6, {"name": "Stop B"})],
        "bus_source": {"source": "gtfs_pune_pmpml", "operator": "PMPML", "tier": "secondary",
                       "license": "MIT-0", "fetched_at": "2026-09-29"},
        "highways": [([[(73.7, 18.4), (73.75, 18.45)], [(73.8, 18.5), (73.85, 18.55)]],
                      {"ref": "NH48", "status": "operational", "kind": "nh_segment"})],
        "toll_plazas": [(73.77777, 18.33333, {"name": None})],
    }
    return cfg, cities, cells, memberships, assets


def test_city_record_reconciles_with_its_areas_and_assets(tmp_path, synthetic_world):
    cfg, cities, cells, memberships, assets = _world_with_assets(synthetic_world)
    cells.loc[4, "nh_access"] = 10.0  # exactly on the 10 km band: inside it
    write_fixtures(tmp_path, cfg, cities, cells, memberships, assets, "2026-09-29")
    city = {c["id"]: c for c in _read(tmp_path, "cities.json")}["alpha"]
    feats = [f["properties"] for f in _read(tmp_path, "areas/alpha.geojson.gz")["features"]]
    pops = {p["id"]: p["pop"] for p in feats}
    for pid in cfg.presets:
        s = city["scores"][pid]
        mean = sum(p["pop"] * p["sc"][pid] for p in feats) / sum(pops.values())
        assert abs(s["score"] - mean) <= 0.15  # population-weighted mean of the stored areas
        top = max((p for p in feats if p["elig"]), key=lambda p: p["sc"][pid])
        assert s["best_area"] == {"id": top["id"], "name": top["name"], "score": top["sc"][pid]}
        assert sum(d["points"] for d in s["drivers"]) <= s["score"] + 0.2  # top 3 of the points
    # 9000 people at 1 km and 6000 at 4 km from a highway, 1200 at 30 km: the median resident is
    # at 1 km, and the 10 km band holds 15000 of 16200 residents
    # sub-score: (9000 x 95 + 6000 x 76.67 + 1200 x 0) / 16200 = 81.2
    nh = city["factors"]["nh_access"]
    assert nh == {"value": 1.0, "unit": "km", "share": 0.93, "band_km": 10, "subscore": 81.2}
    assert city["factors"]["road_strength"]["share"] is None
    assert city["data"] == {"bus": {"operator": "PMPML", "tier": "secondary", "stops": 2},
                            "metro_stations": 1, "rail_stations": 1}
    assert city["cells"] == 3 and city["population"] == 300000
    assert all(type(v) is int for v in (city["cells"], city["population"], *pops.values()))
    assert city["source"].endswith("+gtfs") and "MIT-0" in city["license"]
    assert "Vonter/bmrcl-gtfs" in city["license"]  # a GTFS station's feed counts too, not only the bus
    beta = {c["id"]: c for c in _read(tmp_path, "cities.json")}["beta"]
    assert beta["data"]["bus"] is None and not beta["source"].endswith("+gtfs")
    # rail is unobserved for 8000 of beta's 14400 residents: the share is of the 6400 observed
    assert beta["factors"]["rail_access"]["share"] == 0.81  # 5200 / 6400 within 2 km
    assert beta["factors"]["nh_access"]["share"] == 0.92  # 13200 / 14400, the 10 km cell included


def test_assets_carry_provenance_and_the_bus_feed_only_as_its_public_fields(tmp_path, synthetic_world):
    cfg, cities, cells, memberships, assets = _world_with_assets(synthetic_world)
    write_fixtures(tmp_path, cfg, cities, cells, memberships, assets, "2026-09-29")
    a = _read(tmp_path, "assets/alpha.json.gz")
    assert (a["city"], a["source"], a["fetched_at"]) == ("alpha", "osm+gtfs", "2026-09-29")
    assert a["license"].startswith("ODbL-1.0") and "MIT-0" in a["license"]
    assert a["bus_source"] == {"operator": "PMPML", "tier": "secondary", "license": "MIT-0",
                               "fetched_at": "2026-09-29"}
    (highway,) = a["highways"]["features"]
    assert highway["geometry"]["type"] == "MultiLineString"
    assert a["toll_plazas"]["features"][0]["geometry"]["coordinates"] == [73.7778, 18.3333]
    assert a["toll_plazas"]["features"][0]["properties"] == {"name": None}  # unknown, not invented
    b = _read(tmp_path, "assets/beta.json.gz")
    assert b["bus_stops"] is None and b["bus_source"] is None and b["license"] == "ODbL-1.0"
    sources = {s["id"]: s for s in _read(tmp_path, "meta.json")["sources"]}
    assert {"osm_india", "worldpop_india_2020_1km", "gtfs_pune_pmpml", "gtfs_bengaluru_bmrcl"} <= set(sources)
    assert all(s["name"] and s["license"] and s["attribution"] for s in sources.values())


def test_every_preset_has_drivers_and_gaps_in_every_area(tmp_path, synthetic_world):
    cfg, cities, cells, memberships, assets = synthetic_world
    write_fixtures(tmp_path, cfg, cities, cells, memberships, assets, "2026-09-29")
    for city in ("alpha", "beta"):
        for feat in _read(tmp_path, f"areas/{city}.geojson.gz")["features"]:
            p = feat["properties"]
            assert set(p["d"]) == set(p["g"]) == set(p["sc"]) == set(p["ac"]) == set(cfg.presets)
            for gaps in p["g"].values():
                assert all(v == p["s"][f] for f, v in gaps)  # a gap's value is its stored sub-score


def test_areas_become_eligible_only_from_best_area_min_population(tmp_path, synthetic_world):
    cfg, cities, cells, memberships, assets = synthetic_world
    extra = pd.DataFrame({"city_id": ["alpha", "alpha"], "cell": list(cells["cell"][3:])})
    memberships = pd.concat([memberships, extra], ignore_index=True)  # alpha: four cells >= 5,000
    cells.loc[1, "pop"] = 5000.0  # exactly the threshold: eligible
    cells.loc[2, list(cfg.factors)] = [0.1, 0.1, 0.1, 3.0, 20.0]  # the 1,200-people cell scores best
    write_fixtures(tmp_path, cfg, cities, cells, memberships, assets, "2026-09-29")
    elig = {f["properties"]["pop"]: f["properties"]["elig"]
            for f in _read(tmp_path, "areas/alpha.geojson.gz")["features"]}
    assert elig == {9000: True, 5000: True, 1200: False, 8000: True, 5200: True}
    alpha = {c["id"]: c for c in _read(tmp_path, "cities.json")}["alpha"]
    assert all(s["best_area"]["id"] != cells.loc[2, "cell"] for s in alpha["scores"].values())
    beta = _read(tmp_path, "areas/beta.geojson.gz")["features"]
    assert all(f["properties"]["elig"] for f in beta)  # only two of three qualify: all eligible


def test_area_geometry_is_a_closed_counter_clockwise_hexagon(tmp_path, synthetic_world):
    cfg, cities, cells, memberships, assets = synthetic_world
    write_fixtures(tmp_path, cfg, cities, cells, memberships, assets, "2026-09-29")
    for feat in _read(tmp_path, "areas/alpha.geojson.gz")["features"]:
        (ring,) = feat["geometry"]["coordinates"]
        assert len(ring) == 7 and ring[0] == ring[-1]
        assert all(round(v, 4) == v for point in ring for v in point)
        doubled = sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in pairwise(ring))
        assert doubled > 0  # counter-clockwise


def test_values_are_rounded_and_never_negative_zero(tmp_path, synthetic_world):
    cfg, cities, cells, memberships, assets = synthetic_world
    cells.loc[0, "built_up_growth"] = -0.04  # GHSL can lose built-up area; rounds to 0.0, not -0.0
    cells.loc[0, "nh_access"] = 1.23456
    write_fixtures(tmp_path, cfg, cities, cells, memberships, assets, "2026-09-29")
    raw = gzip.decompress((tmp_path / "areas" / "alpha.geojson.gz").read_bytes()).decode()
    assert "-0.0" not in raw
    (p,) = [f["properties"] for f in json.loads(raw)["features"] if f["properties"]["name"] == "Baner"]
    assert p["f"]["built_up_growth"] == 0.0 and p["f"]["nh_access"] == 1.2


def _orphan_member(cells, memberships, assets):
    memberships.loc[0, "cell"] = "87608850effffff"  # no row in `cells`


def _bus_stops_without_source(cells, memberships, assets):
    assets["alpha"]["bus_stops"] = [(73.8, 18.5, {"name": "Stop"})]


def _cell_below_min_population(cells, memberships, assets):
    cells.loc[0, "pop"] = 999.0


@pytest.mark.parametrize(
    "spoil", [_orphan_member, _bus_stops_without_source, _cell_below_min_population]
)
def test_inputs_the_api_would_reject_raise_and_keep_the_old_tree(tmp_path, synthetic_world, spoil):
    cfg, cities, cells, memberships, assets = synthetic_world
    write_fixtures(tmp_path, cfg, cities, cells, memberships, assets, "2026-09-29")
    before = (tmp_path / "cities.json").read_bytes()
    spoil(cells, memberships, assets)
    with pytest.raises(ValueError, match="rejected"):
        write_fixtures(tmp_path, cfg, cities, cells, memberships, assets, "2026-09-30")
    assert (tmp_path / "cities.json").read_bytes() == before


def test_a_tree_over_budget_is_never_published(tmp_path, synthetic_world):
    cfg, cities, cells, memberships, assets = synthetic_world
    write_fixtures(tmp_path, cfg, cities, cells, memberships, assets, "2026-09-29")
    (tmp_path / "stale.json").write_text("{}")  # a re-run replaces the whole tree
    write_fixtures(tmp_path, cfg, cities, cells, memberships, assets, "2026-09-29")
    assert not (tmp_path / "stale.json").exists()
    assert [p.name for p in tmp_path.parent.iterdir() if p.name.startswith(f".{tmp_path.name}.")] == []
    cfg.raw["pipeline"]["max_file_mb"] = 0.001  # 1,000 bytes: cities.json no longer fits
    with pytest.raises(ValueError, match="over 1,000 bytes"):
        write_fixtures(tmp_path, cfg, cities, cells, memberships, assets, "2026-09-30")
    assert _read(tmp_path, "meta.json")["as_of"] == "2026-09-29"
    cfg.raw["pipeline"].update(max_file_mb=5, max_dir_mb=0.01)  # 10,000 bytes: a few 4 KiB blocks
    with pytest.raises(ValueError, match="on disk"):
        write_fixtures(tmp_path, cfg, cities, cells, memberships, assets, "2026-09-30")


def test_weighted_median_is_an_observed_value():
    values = np.array([5.0, 1.0, 3.0])
    assert weighted_median(values, np.array([1.0, 1.0, 1.0])) == 3.0
    assert weighted_median(values, np.array([10.0, 1.0, 1.0])) == 5.0
    assert weighted_median(np.array([1.0, 2.0]), np.array([1.0, 1.0])) == 1.0  # lower median


# --- the pipeline steps' pure helpers (pipeline.invest.build) -----------------------------------


def test_piece_table_sums_people_and_weights_the_centre():
    from affine import Affine

    from pipeline.invest.build import piece_table

    labels = np.array([[1, 1, 0], [0, 2, 2]])
    people = np.array([[10.0, 30.0, 5.0], [7.0, 20.0, 20.0]])
    t = piece_table(people, labels, Affine(1, 0, 0, 0, -1, 2))  # pixel centres at x + 0.5
    assert t["population"].tolist() == [40.0, 40.0]  # the 5 and 7 outside every piece are not counted
    assert t["centroid_lon"].tolist() == [1.25, 2.0] and t["centroid_lat"].tolist() == [1.5, 0.5]


def test_area_cells_are_the_core_and_its_rings_once_each():
    from pipeline.invest.build import area_cells

    core = h3.latlng_to_cell(18.5, 73.8, 7)
    neighbour = h3.grid_ring(core, 1)[0]
    assert area_cells([core], 1) == sorted(h3.grid_disk(core, 1))
    assert area_cells([core, neighbour], 1) == sorted(set(h3.grid_disk(core, 1)) | set(h3.grid_disk(neighbour, 1)))


def test_pixels_near_reaches_every_pixel_of_the_cell():
    from affine import Affine

    from pipeline.invest.build import pixels_near

    transform, shape = Affine(0.01, 0, 73.6, 0, -0.01, 18.8), (60, 60)  # ≈1.1 km pixels
    cell = h3.latlng_to_cell(18.5, 73.9, 7)
    lat, lon = h3.cell_to_latlng(cell)
    rows, cols, plon, plat = pixels_near(pd.DataFrame({"lat": [lat], "lon": [lon]}), transform, "EPSG:4326", shape)
    everywhere = [(r, c) for r in range(shape[0]) for c in range(shape[1])
                  if h3.latlng_to_cell(18.8 - 0.01 * (r + 0.5), 73.6 + 0.01 * (c + 0.5), 7) == cell]
    assert everywhere and set(everywhere) <= set(zip(rows.tolist(), cols.tolist(), strict=True))
    assert np.allclose(plon, 73.6 + 0.01 * (cols + 0.5)) and np.allclose(plat, 18.8 - 0.01 * (rows + 0.5))


def test_highways_are_clipped_merged_per_road_and_keep_a_missing_ref_unknown():
    import geopandas as gpd
    import shapely

    from pipeline.invest.build import _highways

    segments = gpd.GeoDataFrame(
        {"ref": ["NH48", "NH48", None], "status": ["operational"] * 3, "kind": ["nh_segment"] * 3},
        geometry=[shapely.LineString([(0, 0), (1, 0)]), shapely.LineString([(1, 0), (3, 0)]),
                  shapely.LineString([(0, 1), (1, 1)])],
        crs="EPSG:4326",
    )
    out = _highways(segments, shapely.STRtree(segments.geometry.to_numpy()), (0.5, -1, 2, 2), 0.001)
    assert sorted((p["ref"] or "", lines) for lines, p in out) == [
        ("", [[(0.5, 1.0), (1.0, 1.0)]]),
        ("NH48", [[(0.5, 0.0), (2.0, 0.0)]]),  # two pieces merged into one line, cut at the box
    ]


def test_sensitivity_city_scores_are_the_exported_city_scores(tmp_path, synthetic_world):
    from pipeline.invest.build import city_scores

    cfg, cities, cells, memberships, assets = synthetic_world
    write_fixtures(tmp_path, cfg, cities, cells, memberships, assets, "2026-09-29")
    exported = {c["id"]: c["scores"] for c in _read(tmp_path, "cities.json")}
    weights = np.array([[p.weights[f] for f in cfg.factors] for p in cfg.presets.values()])
    ours = city_scores(cfg, cells, memberships, ["alpha", "beta"], weights)
    for i, city in enumerate(["alpha", "beta"]):
        for j, pid in enumerate(cfg.presets):
            assert abs(ours[i, j] - exported[city][pid]["score"]) <= 0.05  # only the 1-decimal rounding


def test_sensitivity_report_covers_states_with_five_cities():
    from pipeline.invest.build import sensitivity_report

    cfg = load_config()
    rng = np.random.default_rng(0)
    ids = [h3.latlng_to_cell(18.0 + 0.1 * i, 74.0, 7) for i in range(7)]
    cells = pd.DataFrame({"cell": ids, "pop": 2000.0, **{f: rng.uniform(0, 20, 7) for f in cfg.factors}})
    cities = pd.DataFrame({"id": [f"c{i}" for i in range(7)], "state": ["MH"] * 6 + ["GA"]})
    memberships = pd.DataFrame({"city_id": cities["id"], "cell": ids})
    report = sensitivity_report(cfg, cities, cells, memberships)
    rows = [line for line in report.splitlines() if line.startswith("| MH |")]
    assert len(rows) == 1 and "| GA |" not in report  # Goa has fewer than 5 cities
    assert all(0 <= float(v) <= 1 for v in rows[0].split("|")[3:-1])
    assert "| balanced | 1.00 |" in report  # a preset agrees with itself
