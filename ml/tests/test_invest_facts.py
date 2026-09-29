import geopandas as gpd
import h3
import numpy as np
import pandas as pd
import pytest
from shapely.geometry import LineString, Point

from fields.national_highways import cell_facts as nh
from fields.public_transport import cell_facts as pt
from pipeline.invest import facts as facts_module
from pipeline.invest.facts import (
    _check_facts_config,
    cell_centres,
    facts_config,
    growth_pp,
    km_per_km2,
    mean_by_cell,
    name_cells,
    sum_by_cell,
)
from pipeline.invest.geo import nearest, nearest_km

RES = 7


def test_nearest_km_to_a_line_and_a_point():
    centres = pd.DataFrame({"lat": [18.51, 18.50], "lon": [73.9, 73.9]})
    line = gpd.GeoSeries([LineString([(73.8, 18.5), (74.0, 18.5)])], crs="EPSG:4326")
    d = nearest_km(centres, line)
    assert d.iloc[0] == pytest.approx(1.11, abs=0.06)  # 0.01° of latitude
    assert d.iloc[1] == pytest.approx(0.0, abs=0.01)
    pts = gpd.GeoSeries([Point(73.91, 18.50)], crs="EPSG:4326")
    assert nearest_km(centres.iloc[[1]], pts).iloc[0] == pytest.approx(1.06, abs=0.06)  # 0.01° of longitude


def test_nearest_km_without_targets_is_unobserved_not_zero():
    centres = pd.DataFrame({"lat": [18.5], "lon": [73.9]})
    assert nearest_km(centres, gpd.GeoSeries([], crs="EPSG:4326")).isna().all()


def test_mean_and_sum_by_cell_group_points_by_h3_cell():
    cell = h3.latlng_to_cell(18.5, 73.8, RES)
    lons, lats, vals = [73.8, 73.8001, 90.0], [18.5, 18.5001, 10.0], [100.0, 300.0, 5.0]
    assert mean_by_cell(lons, lats, vals, RES)[cell] == pytest.approx(200.0)
    assert sum_by_cell(lons, lats, vals, RES)[cell] == pytest.approx(400.0)


def test_growth_pp_is_change_in_built_up_share():
    cell = "8760e6a5bffffff"
    b2000, b2020 = pd.Series({cell: 100_000.0}), pd.Series({cell: 300_000.0})  # m² per 1 km² pixel
    assert growth_pp(b2000, b2020)[cell] == pytest.approx(20.0)


def test_km_per_km2_divides_by_the_cell_area():
    cell = h3.latlng_to_cell(18.5, 73.8, RES)
    area = h3.cell_area(cell, "km^2")
    assert km_per_km2(pd.Series({cell: 10.0}))[cell] == pytest.approx(10.0 / area)


def test_name_cells_prefers_inside_then_rank_then_nearest_then_none():
    inside = h3.latlng_to_cell(18.55, 73.80, RES)
    outside = h3.latlng_to_cell(18.70, 73.80, RES)
    empty = h3.latlng_to_cell(19.50, 74.50, RES)
    cells = pd.DataFrame(
        [(c, *h3.cell_to_latlng(c)) for c in (inside, outside, empty)], columns=["cell", "lat", "lon"]
    )
    lat, lon = h3.cell_to_latlng(inside)
    places = pd.DataFrame(
        {
            "lon": [lon, lon + 0.002, 73.80],
            "lat": [lat, lat + 0.002, 18.71],
            "name": ["Pashan", "Baner", "Talegaon"],
            "place": ["village", "suburb", "town"],  # a suburb outranks a village inside the same cell
        }
    )
    names = name_cells(cells, places)
    assert names[inside] == "Baner"
    assert names[outside] == "Talegaon"  # nothing inside; nearest place within 2.5 km
    assert names[empty] is None


# --- beyond the brief: what the verbatim tests above do not reach ---------------------------------


def test_nearest_reports_the_target_and_leaves_bad_or_unreachable_centres_unobserved():
    targets = gpd.GeoSeries([Point(73.9, 18.5), Point(74.5, 18.5)], crs="EPSG:4326")
    lats, lons = [18.5, float("nan"), 18.5, 19.5], [73.91, 73.9, 74.51, 74.5]
    centres = pd.DataFrame({"lat": lats, "lon": lons}, index=list("abcd"))
    hit = nearest(centres, targets, max_km=5)
    assert hit["pos"].isna().tolist() == [False, True, False, True]  # NaN centre; 111 km from any
    assert hit.loc[["a", "c"], "pos"].tolist() == [0, 1]
    assert hit["km"].isna().tolist() == [False, True, False, True]
    assert hit.loc["a", "km"] == pytest.approx(1.06, abs=0.06)  # 0.01° of longitude


def test_cell_centres_are_the_lat_lon_of_each_cell():
    cell = h3.latlng_to_cell(18.5, 73.8, RES)
    centre = cell_centres([cell]).iloc[0]
    assert (centre["lat"], centre["lon"]) == pytest.approx(h3.cell_to_latlng(cell))
    assert h3.latlng_to_cell(centre["lat"], centre["lon"], RES) == cell


def test_cell_centres_are_indexed_by_cell_so_per_cell_series_line_up():
    a, b = h3.latlng_to_cell(18.5, 73.8, RES), h3.latlng_to_cell(19.0, 75.0, RES)
    centres = cell_centres([b, a])  # deliberately not in sorted order
    assert centres.index.tolist() == [b, a] and centres["cell"].tolist() == [b, a]
    lat, lon = h3.cell_to_latlng(a)
    pop = sum_by_cell([lon], [lat], [7.0], RES)  # indexed by cell id, and only `a` has people
    near = nearest_km(centres, gpd.GeoSeries([Point(lon, lat)], crs="EPSG:4326"))  # like centres
    joined = centres.assign(pop=pop, near=near)  # a RangeIndex here would turn every value to NaN
    assert joined.loc[a, "pop"] == 7.0 and np.isnan(joined.loc[b, "pop"])
    assert joined.loc[a, "near"] == pytest.approx(0.0, abs=0.01) and joined.loc[b, "near"] > 100
    # the index has no name, so "cell" is one ordinary column: these would raise as ambiguous if
    # the index were called "cell" too
    assert centres.merge(pd.DataFrame({"cell": [a], "x": [1]}), on="cell")["x"].tolist() == [1]
    assert centres.sort_values("cell")["cell"].tolist() == sorted([a, b])
    assert centres.groupby("cell")["lat"].first().index.tolist() == sorted([a, b])


def test_unobserved_stays_unobserved_through_the_aggregations():
    cell = h3.latlng_to_cell(18.5, 73.8, RES)
    lons, lats, nans = [73.8, 73.8001], [18.5, 18.5001], [float("nan")] * 2
    assert pd.isna(mean_by_cell(lons, lats, nans, RES)[cell])
    assert pd.isna(sum_by_cell(lons, lats, nans, RES)[cell])  # not 0
    both = growth_pp(pd.Series({"a": 1e5, "b": 2e5}), pd.Series({"a": 3e5}))
    assert both.isna().tolist() == [False, True]  # a cell missing from a year has no growth
    with pytest.raises(ValueError):
        mean_by_cell(lons, lats, [1.0], RES)  # one value per point


def _one_cell(lat=19.0, lon=75.0):
    cell = h3.latlng_to_cell(lat, lon, RES)
    centre = h3.cell_to_latlng(cell)
    return cell, centre, pd.DataFrame({"cell": [cell], "lat": [centre[0]], "lon": [centre[1]]})


def test_name_cells_falls_back_to_the_nearest_place_of_any_rank_within_reach():
    cell, (lat, lon), cells = _one_cell()
    km = 1 / 111.19  # degrees of latitude per km; a res-7 cell reaches 1.4 km from its centre
    places = pd.DataFrame(
        {
            "lon": [lon] * 3,
            "lat": [lat + 1.9 * km, lat - 2.2 * km, lat + 3.0 * km],
            "name": ["Hamletpur", "Suburbia", "Farville"],
            "place": ["hamlet", "suburb", "village"],
        }
    )
    assert name_cells(cells, places)[cell] == "Hamletpur"  # nearest wins; a suburb 2.2 km out loses
    assert name_cells(cells, places.iloc[[2]])[cell] is None  # 3.0 km is out of reach
    assert name_cells(cells, places.iloc[[2]], max_km=3.5)[cell] == "Farville"


def test_name_cells_ignores_non_names_and_rejects_mixed_resolutions():
    cell, (lat, lon), cells = _one_cell()
    km = 1 / 111.19
    places = pd.DataFrame(
        {
            "lon": [lon] * 4,
            "lat": [lat, lat, lat + 1.6 * km, lat - 2.0 * km],
            "name": ["Farm Lane", None, "Farmstead", "Ward Nine"],
            "place": ["farm", "suburb", "farm", "quarter"],  # two farms, an unnamed suburb, a ward
        }
    )
    # inside the cell only the farm and the unnamed suburb; the nearer outside place is a farm too
    assert name_cells(cells, places)[cell] == "Ward Nine"
    named_index = cells.set_index("cell", drop=False)  # an index called "cell" must not break it
    assert name_cells(named_index, places)[cell] == "Ward Nine"
    assert name_cells(cells, places.iloc[:0])[cell] is None  # a region with no places at all
    assert name_cells(cells.iloc[:0], places).empty
    finer_cell = h3.latlng_to_cell(lat, lon, RES + 1)
    finer = pd.DataFrame({"cell": [finer_cell], "lat": [lat], "lon": [lon]})
    with pytest.raises(ValueError, match="resolution"):
        name_cells(pd.concat([cells, finer]), places)


def test_facts_config_is_read_from_scoring_yaml_and_rejects_bad_numbers():
    cfg = facts_config()
    assert set(cfg) == {"station_dedupe_m", "station_name_merge_m", "place_name_max_km"}
    bad_configs = (
        {},  # a missing section
        {**cfg, "station_dedupe_m": 0},
        {**cfg, "place_name_max_km": "2.5 km"},
        {**cfg, "station_name_merge_m": -1},
    )
    for bad in bad_configs:
        with pytest.raises(ValueError, match="facts"):
            _check_facts_config(bad)


def test_name_cells_radius_comes_from_config_unless_given(monkeypatch):
    cell, (lat, lon), cells = _one_cell()
    km = 1 / 111.19
    places = pd.DataFrame(  # 1.9 km from the centre: outside the cell, so only the radius decides
        {"lon": [lon], "lat": [lat + 1.9 * km], "name": ["Hamletpur"], "place": ["hamlet"]}
    )
    cfg = facts_config()
    monkeypatch.setattr(facts_module, "facts_config", lambda: {**cfg, "place_name_max_km": 1.0})
    assert name_cells(cells, places)[cell] is None  # the configured radius is 1 km
    assert name_cells(cells, places, max_km=3.0)[cell] == "Hamletpur"  # an explicit radius wins
    monkeypatch.setattr(facts_module, "facts_config", lambda: {**cfg, "place_name_max_km": 3.0})
    assert name_cells(cells, places)[cell] == "Hamletpur"


# --- national highways: OSM-derived, open roads only (ADR-0014) -----------------------------------


@pytest.fixture
def nh_dir(tmp_path, monkeypatch):
    """A stand-in for data/processed/national_highways holding only the two OSM-derived files the
    facts may read: any read of nhai_*.parquet would raise FileNotFoundError."""
    monkeypatch.setattr(nh, "OUT", tmp_path)
    return tmp_path


def _write_segments(directory, rows):
    """rows: (kind, status, eff_km, LineString) -> nh_segments.parquet."""
    kinds, statuses, eff_km, lines = zip(*rows, strict=True)
    gdf = gpd.GeoDataFrame(
        {"kind": kinds, "status": statuses, "eff_km": eff_km}, geometry=list(lines), crs="EPSG:4326"
    )
    gdf.to_parquet(directory / "nh_segments.parquet")


def _write_context(directory, rows):
    """rows: (way_id, pos, lon, lat) -> osm_context_way_nodes.parquet."""
    df = pd.DataFrame(rows, columns=["way_id", "pos", "lon", "lat"])
    df["node_id"] = np.arange(len(df))
    df.to_parquet(directory / "osm_context_way_nodes.parquet")


def _east_west(lat, lon0=73.80, lon1=73.85):
    return LineString([(lon0, lat), (lon1, lat)])


def test_nh_access_measures_to_operational_highways_only(nh_dir):
    _write_segments(
        nh_dir,
        [
            ("nh_segment", "operational", 1.0, _east_west(18.50)),
            ("nh_segment", "under_construction", 1.0, _east_west(18.521)),  # nearest, but not open
            ("nh_segment", "proposed", 1.0, _east_west(18.5205)),
            ("nh_connector", "operational", 1.0, _east_west(18.5202)),  # open, but not an NH kind
            ("expressway_segment", "operational", 1.0, _east_west(18.60)),
        ],
    )
    centres = pd.DataFrame({"lat": [18.52, 18.61], "lon": [73.82, 73.82]})
    d = nh.nh_access_km(centres)
    assert d.iloc[0] == pytest.approx(2.22, abs=0.1)  # 0.02° of latitude to the open NH
    assert d.iloc[1] == pytest.approx(1.11, abs=0.06)  # an operational expressway counts


def test_arterial_km_spreads_open_nh_along_its_line_and_adds_context_ways(nh_dir):
    line = _east_west(18.50, 73.80, 73.90)  # about 10.5 km, five or six cells
    _write_segments(
        nh_dir,
        [
            ("nh_segment", "operational", 5.0, line),  # a divided road drawn twice: 5 effective km
            ("nh_segment", "under_construction", 100.0, _east_west(18.0, 73.0, 73.1)),
        ],
    )
    _write_context(  # shuffled on purpose; way 8 has one node, and way 9 lies far from way 7
        nh_dir,
        [
            (7, 2, 73.8, 18.61), (7, 1, 73.8, 18.60), (7, 3, 73.8, 18.62), (8, 1, 75.0, 19.0),
            (9, 1, 76.0, 20.0), (9, 2, 76.0, 20.01),
        ],
    )  # fmt: skip
    km = nh.arterial_km_by_cell(RES)

    # three 0.01° segments; a sphere overstates a degree of latitude here by 0.5% against WGS84
    ctx = 3 * h3.great_circle_distance((18.60, 73.8), (18.61, 73.8), unit="km")
    assert km.sum() == pytest.approx(5.0 + ctx, rel=1e-2)  # closed and unbuilt NH add nothing
    on_line = pd.Series(
        [h3.latlng_to_cell(18.5, lon, RES) for lon in np.linspace(73.8, 73.9, 2000)]
    ).value_counts(normalize=True)
    for cell, share in on_line.items():
        assert km[cell] == pytest.approx(5.0 * share, abs=0.15)  # by where the road runs
    assert km.drop(on_line.index).sum() == pytest.approx(ctx, rel=1e-2)  # the rest is context


def _way(way_id, lon, lat0, lat1):
    """A two-node north-south way, in drawing order: (way_id, pos, lon, lat) rows."""
    return [(way_id, 1, lon, lat0), (way_id, 2, lon, lat1)]


def test_arterial_km_counts_a_divided_road_once(nh_dir):
    _write_segments(  # far from the ways below: the highway is not what this test is about
        nh_dir, [("nh_segment", "operational", 1.0, _east_west(10.0, 77.0, 77.01))]
    )
    gap = 21 / 105_400  # about 21 m of longitude, inside the 30 m a partner carriageway may be
    groups = {
        "one node": [(0, 1, 75.0, 18.605)],  # no length, and sorted before the pair below
        "divided": [*_way(1, 73.80, 18.60, 18.61), *_way(2, 73.80 + gap, 18.61, 18.60)],
        "lone": _way(3, 74.00, 18.60, 18.61),
        "same direction": [*_way(4, 74.20, 18.60, 18.61), *_way(5, 74.20 + gap, 18.60, 18.61)],
        "far apart": [*_way(6, 74.40, 18.60, 18.61), *_way(7, 74.403, 18.61, 18.60)],  # 316 m
    }
    ways_counted = {"one node": 0, "divided": 1, "lone": 1, "same direction": 2, "far apart": 2}
    _write_context(nh_dir, [row for rows in groups.values() for row in rows])
    km = nh.arterial_km_by_cell(RES)

    one_way = h3.great_circle_distance((18.60, 73.8), (18.61, 73.8), unit="km")
    for name, rows in groups.items():
        cells = list({h3.latlng_to_cell(18.605, lon, RES) for _, _, lon, _ in rows})
        # opposite ways 21 m apart are the two carriageways of one road: half each, one road's km;
        # ways that run the same direction, or lie far apart, are separate roads: all of their km
        assert km.reindex(cells).sum() == pytest.approx(ways_counted[name] * one_way, rel=1e-2), name


# --- public transport: stations and bus stops -----------------------------------------------------


@pytest.fixture
def pt_files(tmp_path, monkeypatch):
    monkeypatch.setattr(pt, "OSM_STATIONS", tmp_path / "osm_stations.parquet")
    monkeypatch.setattr(pt, "GTFS_STOPS", tmp_path / "gtfs_stops.parquet")
    return tmp_path


def _east(metres, lon0=73.8):
    return lon0 + metres / 105_400  # a degree of longitude is about 105.4 km at 18.5°N


def _write_osm(directory, rows):
    """rows: (lon, name, mode) at 18.5°N."""
    lons, names, modes = zip(*rows, strict=True)
    df = pd.DataFrame({"lon": lons, "lat": 18.5, "name": names, "mode": modes})
    df.assign(node_id=np.arange(len(df))).to_parquet(directory / "osm_stations.parquet")


def _write_gtfs(directory, rows):
    """rows: (lon, lat, name, mode, feed[, location_type]) -> gtfs_stops.parquet with the columns
    the facts read."""
    lons, lats, names, modes, feeds, types = zip(*(r + (None,) * (6 - len(r)) for r in rows))
    df = pd.DataFrame(
        {"stop_lon": lons, "stop_lat": lats, "stop_name": names, "mode": modes, "source": feeds}
    )
    df["location_type"] = types
    df["operator"] = df["source"].str.removeprefix("gtfs_test_").str.upper()
    df["tier"], df["license"] = "secondary", "test-license"
    df["fetched_at"] = "2026-09-29T00:00:00Z"
    df.to_parquet(directory / "gtfs_stops.parquet")


def test_load_stations_dedupes_within_the_configured_distance_keeping_named_osm_first(
    pt_files, monkeypatch
):
    cfg = facts_config()
    d = cfg["station_dedupe_m"]  # every distance below is a multiple of it
    _write_osm(
        pt_files,
        [
            (_east(0), None, "rail"),  # unnamed node beside the named ones
            (_east(0.4 * d), "District Court", "rail"),  # named, first in order: wins the cluster
            (_east(0.8 * d), "District Court", "rail"),  # 0.4 d from the winner
            (_east(6 * d), "Swargate", "rail"),
            (_east(30 * d), None, "rail"),  # alone: kept, and its name is None (not NaN)
            (_east(0.2 * d), "Vanaz", "metro"),
        ],
    )
    rail = pt.load_stations("rail")
    assert rail["name"].tolist() == ["District Court", "Swargate", None]
    assert rail["name"].iloc[2] is None and set(rail["source"]) == {"osm_india"}
    assert list(rail.columns) == ["lon", "lat", "name", "source"]
    # the distance is read from config at call time, not fixed in the module
    with monkeypatch.context() as patch:
        patch.setattr(pt, "facts_config", lambda: {**cfg, "station_dedupe_m": 0.01 * d})
        assert len(pt.load_stations("rail")) == 5  # a 1% distance merges none of the five nodes

    _write_gtfs(
        pt_files,
        [
            (_east(0.2 * d), 18.5, "Vanaz Platform 1", "metro", "gtfs_test_hmrl"),  # OSM's station
            (_east(20 * d), 18.5, "Ideal Colony", "metro", "gtfs_test_hmrl", "1"),  # a station
            (_east(30 * d), 18.5, "Ideal Colony Arm A Lift", "metro", "gtfs_test_hmrl", "2"),
            (_east(40 * d), 18.5, "Ideal Colony Platform", "metro", "gtfs_test_hmrl", "0"),
            (_east(20 * d), 18.5, "Ideal Colony bus bay", "bus", "gtfs_test_best"),
        ],
    )
    metro = pt.load_stations("metro")
    # the OSM record outranks its GTFS twin; a lift (location_type 2) is no station at all; a
    # station (1) and a platform (0) are both stops, kept because they are 2 km apart here
    assert metro["name"].tolist() == ["Vanaz", "Ideal Colony", "Ideal Colony Platform"]
    assert metro["source"].tolist() == ["osm_india", "gtfs_test_hmrl", "gtfs_test_hmrl"]
    assert len(pt.load_stations("rail")) == 3  # GTFS joins the metro list only
    with pytest.raises(ValueError, match="mode"):
        pt.load_stations("bus")


def test_station_access_uses_the_deduplicated_stations(pt_files):
    d = facts_config()["station_dedupe_m"]
    _write_osm(pt_files, [(_east(6 * d), "Swargate", "rail"), (_east(6.4 * d), "Swargate", "rail")])
    centres = pd.DataFrame({"lat": [18.5], "lon": [_east(7.3 * d)]})
    # the first of the two nodes survives, so 1.3 d away; measured to the raw file it would be 0.9 d
    assert pt.station_access_km(centres, "rail").iloc[0] == pytest.approx(1.3 * d / 1000, abs=0.01)
    assert len(pt.load_stations("rail")) == 1


def test_a_gtfs_stop_repeating_an_osm_station_by_name_merges_within_the_configured_distance(
    pt_files, monkeypatch
):
    cfg = facts_config()
    merge = cfg["station_name_merge_m"]
    near, far = 0.7 * merge, 1.3 * merge
    assert near > cfg["station_dedupe_m"]  # so the name rule, not the proximity rule, does the merging
    _write_osm(
        pt_files,
        [
            (_east(0), "Pachaiyappa's College", "metro"),
            (_east(10_000), "Guindy", "metro"),
            (_east(20_000), "Alandur", "metro"),
            (_east(30_000), "Central", "metro"),
            (_east(30_000 + near), "Central", "metro"),  # two OSM stations that share a name: both stay
            (_east(40_000), None, "metro"),  # unnamed: nothing to match a GTFS stop on
        ],
    )
    _write_gtfs(
        pt_files,
        [
            (_east(near), 18.5, "PACHAIYAPPAS  COLLEGE.", "metro", "gtfs_test_cmrl"),  # same station
            (_east(10_000 + near), 18.5, "Guindy Junction", "metro", "gtfs_test_cmrl"),  # own name
            (_east(20_000 + far), 18.5, "Alandur", "metro", "gtfs_test_cmrl"),  # same name, too far
            (_east(40_000 + near), 18.5, None, "metro", "gtfs_test_cmrl"),  # unnamed beside unnamed
        ],
    )
    metro = pt.load_stations("metro")
    assert metro["name"].tolist() == [
        "Pachaiyappa's College", "Guindy", "Alandur", "Central", "Central", None,  # OSM, all six
        "Guindy Junction", "Alandur", None,  # the GTFS stops that are stations of their own
    ]  # fmt: skip
    assert metro["source"].tolist() == ["osm_india"] * 6 + ["gtfs_test_cmrl"] * 3
    # the distance is read from config at call time: shrunk below the gap, the twin is a station
    with monkeypatch.context() as patch:
        patch.setattr(pt, "facts_config", lambda: {**cfg, "station_name_merge_m": 0.5 * near})
        assert "PACHAIYAPPAS  COLLEGE." in pt.load_stations("metro")["name"].tolist()


def test_bus_stops_are_counted_per_cell_and_grouped_by_feed(pt_files):
    a, b, empty = (h3.latlng_to_cell(lat, 75.0, RES) for lat in (19.0, 19.3, 19.6))
    la, lb = (h3.cell_to_latlng(c) for c in (a, b))
    _write_gtfs(
        pt_files,
        [
            (la[1], la[0], "s1", "bus", "gtfs_test_pmpml"),
            (la[1] + 0.0001, la[0], "s2", "bus", "gtfs_test_pmpml"),
            (la[1] - 0.0001, la[0], "s3", "bus", "gtfs_test_pmpml"),
            (lb[1], lb[0], "s4", "bus", "gtfs_test_best"),
            (la[1], la[0], "metro stop", "metro", "gtfs_test_hmrl"),  # not a bus stop
        ],
    )
    counts = pt.bus_stop_counts([a, b, empty], RES)
    assert counts[a] == 3 and counts[b] == 1
    assert np.isnan(counts[empty])  # nothing recorded there: unobserved, not "0 stops"
    assert pt.bus_feeds_by_cell([a], RES) == {
        "gtfs_test_pmpml": {
            "operator": "PMPML", "tier": "secondary", "license": "test-license",
            "fetched_at": "2026-09-29T00:00:00Z", "stops": 3,
        }
    }  # fmt: skip
    assert set(pt.bus_feeds_by_cell([a, b], RES)) == {"gtfs_test_pmpml", "gtfs_test_best"}
    assert pt.bus_feeds_by_cell([empty], RES) == {}
