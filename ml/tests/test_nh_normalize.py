import numpy as np
import pyproj
import pytest
from shapely import LineString

from common.fetch import matches_kind
from fields.national_highways.normalize import (
    classify_osm,
    dual_carriageway_weights,
    expressway_key,
    lane_band,
    nhai_status,
    ocr_int,
    parse_indian_number,
    parse_lanes,
    parse_rai_annexure,
    parse_refs,
    parse_year,
    plaza_key,
    plaza_name_score,
    road_lanes,
)
from pipeline.shared_layers import CANONICAL_STATES, INDIA_CRS, normalize_state


@pytest.mark.parametrize(
    ("ref", "refs", "rejected"),
    [
        ("NH44", ["NH44"], []),
        ("NH 44", ["NH44"], []),
        ("NH-948A", ["NH948A"], []),
        ("NH07", ["NH7"], []),
        ("NH44;NH48", ["NH44", "NH48"], []),
        ("NH 44;SH 17", ["NH44"], []),
        ("NE-II", ["NE2"], []),
        ("NE4", ["NE4"], []),
        ("NE4C", ["NE4C"], []),
        ("NH65:NH548B", ["NH65", "NH548B"], []),
        ("NH52<unterschiedlich>", [], ["NH52<unterschiedlich>"]),
        ("NH44 Bypass", [], ["NH44 Bypass"]),
        ("SH 17", [], []),
        ("NH44;NH 44", ["NH44"], []),
        (None, [], []),
    ],
)
def test_parse_refs(ref, refs, rejected):
    assert parse_refs(ref) == (refs, rejected)


@pytest.mark.parametrize(
    ("value", "lanes"),
    [("4", 4), ("4L", 4), ("2LPS", 2), ("6 lanes", 6), ("2;3", None), ("0", None), (None, None)],
)
def test_parse_lanes(value, lanes):
    assert parse_lanes(value) == lanes


def test_classify_osm():
    nh = classify_osm({"highway": "trunk", "ref": "NH 44", "lanes": "4", "oneway": "yes"})
    assert nh["kind"] == "nh_segment" and nh["status"] == "operational"
    assert nh["refs"] == ["NH44"] and nh["lanes"] == 4 and nh["oneway"] and nh["owner_level"] == "national"

    trunk_no_ref = classify_osm({"highway": "trunk"})
    assert trunk_no_ref["ref_missing"] and trunk_no_ref["owner_level"] == "national"

    expressway = classify_osm({"highway": "motorway", "name": "Some Expressway"})
    assert expressway["kind"] == "expressway_segment" and expressway["owner_level"] == "unknown"

    trunk_expressway = classify_osm({"highway": "trunk", "expressway": "yes", "ref": "NE4"})
    assert trunk_expressway["kind"] == "expressway_segment" and trunk_expressway["refs"] == ["NE4"]

    building = classify_osm({"highway": "construction", "construction": "motorway"})
    assert building["status"] == "under_construction" and building["kind"] == "expressway_segment"
    assert classify_osm({"highway": "proposed", "proposed": "trunk"})["status"] == "proposed"

    assert classify_osm({"highway": "primary", "ref": "SH 17"}) is None
    assert classify_osm({"highway": "trunk", "ref": "SH 17"}) is None  # state highway tagged trunk
    assert classify_osm({"highway": "trunk", "ref": "N2"}) is None  # Bangladesh, inside the extract
    assert classify_osm({"highway": "trunk", "ref": "NH48;NHX"})["refs"] == ["NH48"]
    garbled = classify_osm({"highway": "trunk", "ref": "NH 48 A B"})  # kept so the bad ref is logged
    assert garbled["ref_missing"] and garbled["rejected_refs"] == ["NH 48 A B"]
    assert classify_osm({"highway": "primary", "ref": "NH 66"})["kind"] == "nh_segment"
    assert classify_osm({"highway": "residential"}) is None
    assert classify_osm({"highway": "construction", "construction": "residential"}) is None


@pytest.mark.parametrize(
    ("text", "value"),
    [("1,46,195", 146195), ("12,123", 12123), ("709", 709), ("15", 15), ("1,4a", None), ("", None)],
)
def test_parse_indian_number(text, value):
    assert parse_indian_number(text) == value


@pytest.mark.parametrize(
    ("value", "band"),
    [("2L", "2"), ("4L", "4"), ("6L", "6+"), ("8L", "6+"), ("IL", "<2"), ("<2L", "<2"),
     ("2 L PS", "2"), ("2/4 L", "unknown"), ("Others", "unknown"), (4, "4"), (None, "unknown"),
     (float("nan"), "unknown")],
)
def test_lane_band(value, band):
    assert lane_band(value) == band


def test_road_lanes_doubles_one_side_of_a_dual_carriageway():
    out = road_lanes([2, 2, 3, None, float("nan")], [0.5, 1.0, 0.5, 0.5, 1.0])
    assert out[:3].tolist() == [4.0, 2.0, 6.0]
    assert np.isnan(out[3:]).all()


@pytest.mark.parametrize(
    ("value", "year"),
    [("2008-11-14", 2008), ("January 23, 2008", 2008), ("2023", 2023), ("soon", None), (None, None)],
)
def test_parse_year(value, year):
    assert parse_year(value) == year


def test_nhai_status():
    assert nhai_status("FY - 25") == "under_construction"
    assert nhai_status("Already Completed") == "operational"
    assert nhai_status("Under Implementation") == "under_construction"
    assert nhai_status("Planned") == "proposed"
    assert nhai_status("") is None
    assert nhai_status(float("nan")) is None
    assert nhai_status(None) is None
    assert nhai_status("Something else") is None


def test_dual_carriageway_weights_pairs_opposite_one_way_lines():
    north = LineString([(0, 0), (0, 1000)])
    south = LineString([(20, 1000), (20, 0)])            # 20 m apart, opposite direction
    lone = LineString([(5000, 0), (5000, 1000)])         # one-way with no partner
    same_dir = LineString([(20_000, 0), (20_000, 1000)])
    same_dir_2 = LineString([(20_020, 0), (20_020, 1000)])  # parallel, same direction: not a pair
    two_way = LineString([(40_000, 0), (40_000, 1000)])
    lines = np.array([north, south, lone, same_dir, same_dir_2, two_way], dtype=object)
    oneway = np.array([True, True, True, True, True, False])
    reversed_ = np.zeros(6, dtype=bool)
    weights = dual_carriageway_weights(lines, oneway, reversed_)
    assert weights.tolist() == [0.5, 0.5, 1.0, 1.0, 1.0, 1.0]


def test_dual_carriageway_weights_respects_reversed_one_way():
    a = LineString([(0, 0), (0, 1000)])
    b = LineString([(20, 0), (20, 1000)])  # drawn the same way but oneway=-1: traffic runs opposite
    weights = dual_carriageway_weights(
        np.array([a, b], dtype=object), np.array([True, True]), np.array([False, True])
    )
    assert weights.tolist() == [0.5, 0.5]


@pytest.mark.parametrize(
    ("name", "canonical"),
    [
        ("Andaman & Nicobar Island", "Andaman and Nicobar Islands"),
        ("ORISSA", "Odisha"),
        ("NCT of Delhi", "Delhi"),
        ("Jammu & Kashmir", "Jammu and Kashmir"),
        ("Dadra & Nagar Haveli", "Dadra and Nagar Haveli and Daman and Diu"),
        ("Tamil Nadu", "Tamil Nadu"),
        ("Atlantis", None),
        (None, None),
    ],
)
def test_normalize_state(name, canonical):
    assert normalize_state(name) == canonical


def test_state_list_and_crs():
    assert len(CANONICAL_STATES) == 36
    assert pyproj.CRS(INDIA_CRS).is_projected


@pytest.mark.parametrize(
    ("head", "kind", "ok"),
    [
        (b"%PDF-1.7 ...", "pdf", True),
        (b"<!DOCTYPE html><html>", "pdf", False),
        (b"<html>not a csv</html>", "text", False),
        (b"State,Accidents\nGoa,10", "text", True),
        (b"PK\x03\x04rest", "zip", True),
        (b"\x00\x00\x00\x0d\x0a\x09OSMHeader", "pbf", True),
    ],
)
def test_matches_kind(head, kind, ok):
    assert matches_kind(head, kind) is ok


def test_gap_edges_joins_dead_ends_that_nearly_touch():
    import networkx as nx
    import pandas as pd

    from fields.national_highways.analysis import gap_edges

    graph = nx.Graph([(1, 2), (3, 4), (5, 6)])
    xy = pd.DataFrame({"x": [0, 1000, 1010, 2000, 5000, 6000], "y": [0] * 6}, index=[1, 2, 3, 4, 5, 6])
    gaps = gap_edges(graph, xy, snap_m=50)
    assert sorted(map(tuple, gaps[["u", "v"]].to_numpy().tolist())) == [(2, 3), (3, 2)]
    assert gaps["km"].round(3).tolist() == [0.01, 0.01]


def test_parse_rai_annexure_fixes_ocr_digits():
    text = """Number of Persons Killed in Road Accidents on National Highways*: 2021 to 2024
Il Karnataka 3,487 4,164 4,383 4,278 6
29 Andaman & Nicobar Islands 4] 11 6 14 33
31 D & N Haveli and Daman & Diu 0 9 2 1 35
Total 3,528 4,184 4,391 4,293"""
    years, rows, totals = parse_rai_annexure(text)
    assert years == [2021, 2022, 2023, 2024]
    assert [r["name"] for r in rows] == ["Karnataka", "Andaman & Nicobar Islands", "D & N Haveli and Daman & Diu"]
    assert rows[1]["values"] == [41, 11, 6, 14]
    assert totals == [3528, 4184, 4391, 4293]
    assert ocr_int("1,2x") is None
    assert normalize_state("D & N Haveli and Daman & Diu") == "Dadra and Nagar Haveli and Daman and Diu"


def test_plaza_key():
    assert plaza_key("Bharthana Toll Plaza") == plaza_key("BHARTHANA FEE PLAZA (NH-48)") == "bharthana"
    assert plaza_key("Ahmedabad (Ring Road) Toll Plaza") == "ahmedabad ring road"
    assert plaza_key(None) == ""


def test_expressway_key():
    assert expressway_key("Delhi–Meerut Expressway") == expressway_key("DELHI-MEERUT EXPRESSWAY") == "delhi meerut"
    assert expressway_key("Yamuna Expressway") == "yamuna"
    assert expressway_key(None) == ""
    assert normalize_state("Panjab") == "Punjab"


def test_plaza_name_score():
    assert plaza_name_score("lakhanpur", "lakhanpur rajbagh") == 1.0
    assert plaza_name_score("aganampudi", "agnampadi") >= 0.82
    assert plaza_name_score("khalapur", "kelapur") < 0.82  # two different Maharashtra plazas
    assert plaza_name_score("ivr", "ivr chennai") < 1.0  # too short to trust containment
