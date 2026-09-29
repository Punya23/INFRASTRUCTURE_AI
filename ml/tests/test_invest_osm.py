import duckdb
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from pipeline.invest import osm
from pipeline.invest.osm import _check_counts, _split, classify_station, place_rank


def test_classify_station():
    assert classify_station({"railway": "station"}) == "rail"
    assert classify_station({"railway": "halt"}) == "rail"
    for kind in ("subway", "light_rail", "monorail"):
        assert classify_station({"railway": "station", "station": kind}) == "metro"
    assert classify_station({"public_transport": "station", "subway": "yes"}) == "metro"
    assert classify_station({"railway": "station", "light_rail": "yes"}) == "metro"
    assert classify_station({"railway": "tram_stop"}) is None
    assert classify_station({"highway": "bus_stop"}) is None
    assert classify_station({"railway": "station", "disused": "yes"}) is None
    assert classify_station({}) is None


# Tag shapes seen in the 2026-09 India PBF that a plain railway=station / public_transport=station
# filter gets wrong: unbuilt metro stations, and bus or ferry stations that share the tag.
@pytest.mark.parametrize(
    ("tags", "expected"),
    [
        ({"railway": "proposed", "public_transport": "station", "subway": "yes"}, None),
        ({"railway": "construction", "public_transport": "station", "subway": "yes"}, None),
        ({"railway": "subway_entrance", "public_transport": "station", "subway": "yes"}, None),
        ({"railway": "station", "station": "subway", "construction": "station"}, None),
        ({"railway": "station", "station": "subway", "construction:railway": "station"}, None),
        ({"railway": "halt", "proposed": "station"}, None),
        ({"railway": "station", "disused:railway": "station"}, None),
        ({"railway": "station", "abandoned": "station"}, None),
        ({"railway": "station", "disused": "no", "construction": "no"}, "rail"),
        ({"railway": "station", "was:name": "Old Name"}, "rail"),
        ({"public_transport": "station", "bus": "yes"}, None),
        ({"public_transport": "station", "ferry": "yes"}, None),
        ({"public_transport": "station"}, None),
        ({"public_transport": "station", "train": "yes"}, "rail"),
        ({"railway": "station", "train": "yes", "subway": "yes"}, "metro"),
    ],
)
def test_classify_station_real_world_shapes(tags, expected):
    assert classify_station(tags) == expected


def test_place_rank_orders_localities_and_ignores_the_rest():
    order = ["suburb", "neighbourhood", "quarter", "village", "town", "hamlet"]
    ranks = [place_rank(p) for p in order]
    assert ranks == sorted(ranks) and len(set(ranks)) == len(order)
    assert place_rank("city") is not None and place_rank("city") > place_rank("hamlet")
    assert place_rank("farm") is None and place_rank("isolated_dwelling") is None


def _scanned_nodes() -> duckdb.DuckDBPyConnection:
    """A `cand` table shaped like the PBF scan (BIGINT id, DOUBLE lon/lat, MAP tags)."""
    con = duckdb.connect()
    con.execute(
        "CREATE TABLE cand (node_id BIGINT, lon DOUBLE, lat DOUBLE, tags MAP(VARCHAR, VARCHAR))"
    )
    con.execute("""
        INSERT INTO cand VALUES
            (1, 73.87, 18.53, MAP {'railway': 'station', 'name': 'पुणे', 'name:en': 'Pune Junction'}),
            (2, 73.85, 18.52,
                MAP {'railway': 'station', 'station': 'subway', 'name': 'Civil Court'}),
            (3, 73.86, 18.51,
                MAP {'public_transport': 'station', 'bus': 'yes', 'name': 'Bus Stand'}),
            (4, 73.84, 18.50, MAP {'railway': 'halt'}),
            (5, 73.80, 18.51, MAP {'place': 'suburb', 'name': 'Kothrud', 'name:en': ' '}),
            (6, 73.81, 18.52, MAP {'place': 'village'}),
            (7, 73.82, 18.53, MAP {'place': 'farm', 'name': 'Old Farm'}),
            (8, 73.83, 18.54, MAP {'place': 'hamlet', 'name': 'वाडी', 'name:en': 'Wadi'})""")
    return con


def test_split_names_and_filters_the_scanned_nodes():
    stations, places = _split(_scanned_nodes())
    # the bus station is gone; a station without a name stays; name:en wins over name
    assert stations[["node_id", "mode"]].values.tolist() == [[1, "rail"], [2, "metro"], [4, "rail"]]
    assert stations["name"].tolist()[:2] == ["Pune Junction", "Civil Court"]
    assert stations["name"].isna().tolist() == [False, False, True]
    # unnamed and non-locality places are dropped; a blank name:en falls back to name
    assert places[["node_id", "name", "place"]].values.tolist() == [
        [5, "Kothrud", "suburb"],
        [8, "Wadi", "hamlet"],
    ]


def test_publish_writes_the_promised_types_and_real_nulls(tmp_path, monkeypatch):
    monkeypatch.setattr(osm, "OUT", tmp_path)
    stations, places = _split(_scanned_nodes())
    osm._publish({"osm_stations.parquet": stations, "osm_places.parquet": places})
    written = sorted(p.name for p in tmp_path.iterdir())
    assert written == ["osm_places.parquet", "osm_stations.parquet"]  # no .tmp left behind
    back = pq.read_table(tmp_path / "osm_stations.parquet")
    assert back.column_names == ["node_id", "lon", "lat", "name", "mode"]
    assert back.schema.types[:3] == [pa.int64(), pa.float64(), pa.float64()]
    assert back["name"].to_pylist() == ["Pune Junction", "Civil Court", None]  # a null, not "nan"
    back = pq.read_table(tmp_path / "osm_places.parquet")
    assert back.column_names == ["node_id", "lon", "lat", "name", "place"]


def test_check_counts_fails_closed_and_names_the_numbers():
    places = pd.DataFrame({"place": ["village"] * 200_000})

    def stations(rail: int, metro: int) -> pd.DataFrame:
        return pd.DataFrame({"mode": ["rail"] * rail + ["metro"] * metro})

    counts = _check_counts(stations(5_000, 400), places)
    assert counts == {"rail": 5_000, "metro": 400, "places": 200_000}
    with pytest.raises(RuntimeError, match="'metro': 399"):
        _check_counts(stations(5_000, 399), places)
    with pytest.raises(RuntimeError, match="'rail': 20001"):
        _check_counts(stations(20_001, 400), places)
    with pytest.raises(RuntimeError, match="'places': 3"):
        _check_counts(stations(5_000, 400), places.head(3))


def test_extract_without_the_pbf_fails_closed_and_writes_nothing(tmp_path, monkeypatch):
    monkeypatch.setattr(osm, "PBF", tmp_path / "missing.osm.pbf")
    monkeypatch.setattr(osm, "OUT", tmp_path / "invest")
    with pytest.raises(FileNotFoundError, match="python -m common.fetch"):
        osm.extract()
    assert not (tmp_path / "invest").exists()
