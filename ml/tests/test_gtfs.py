import zipfile

import pytest

from pipeline.gtfs import FeedError, clean_stops, read_feed, route_lines, validate_feed
from pipeline.shared_layers import INDIA_BOUNDS

BASE = {
    "stops.txt": "stop_id,stop_name,stop_lat,stop_lon\n0012,A,12.90,77.50\n0013,B,12.95,77.55\n"
                 "0014,C,12.99,77.59\n0099,Nowhere,0,0\n",
    "routes.txt": "route_id,route_short_name,route_long_name,route_type\nR1,1,One,3\nR2,2,Two,3\nR3,3,Ghost,3\n",
    "trips.txt": "route_id,trip_id,shape_id\nR1,T1,S1\nR2,T2,\nR2,T3,\n",
    "stop_times.txt": "trip_id,stop_id,stop_sequence\nT1,0012,1\nT1,0013,2\n"
                      "T2,0012,1\nT2,0014,2\nT3,0013,1\nT3,0012,2\nT3,0014,3\n",
    "shapes.txt": "shape_id,shape_pt_lat,shape_pt_lon,shape_pt_sequence\nS1,12.90,77.50,1\nS1,12.92,77.52,2\n"
                  "S1,12.95,77.55,3\n",
}


def _zip(tmp_path, files, folder="feed/"):
    path = tmp_path / "gtfs.zip"
    with zipfile.ZipFile(path, "w") as z:
        for name, text in files.items():
            z.writestr(folder + name, text)
    return path


def test_read_feed_keeps_string_ids_and_finds_subfolder(tmp_path):
    feed = read_feed(_zip(tmp_path, BASE))
    assert feed["stops"]["stop_id"].tolist()[:2] == ["0012", "0013"]


def test_read_feed_rejects_missing_table(tmp_path):
    with pytest.raises(FeedError, match="stop_times"):
        read_feed(_zip(tmp_path, {k: v for k, v in BASE.items() if k != "stop_times.txt"}))


def test_validate_counts_row_problems_and_flags_duplicates(tmp_path):
    feed = read_feed(_zip(tmp_path, BASE))
    checks = {i["check"]: (i["level"], i["count"]) for i in validate_feed(feed, INDIA_BOUNDS)}
    assert checks == {"stop_bad_coordinates": ("warning", 1), "route_without_trips": ("warning", 1)}
    dup = read_feed(_zip(tmp_path, BASE | {"routes.txt": "route_id\nR1\nR1\nR2\n"}))
    dup_checks = {i["check"]: (i["level"], i["count"]) for i in validate_feed(dup, INDIA_BOUNDS)}
    assert dup_checks["duplicate_route_id"] == ("error", 1)


def test_route_lines_use_shape_else_longest_trip_stops(tmp_path):
    feed = read_feed(_zip(tmp_path, BASE))
    stops = clean_stops(feed, INDIA_BOUNDS)
    assert "0099" not in stops["stop_id"].values
    lines = route_lines(feed, stops).set_index("route_id")
    assert lines.loc["R1", "geometry_source"] == "shape" and len(lines.loc["R1", "geometry"].coords) == 3
    assert lines.loc["R2", "geometry_source"] == "stop_sequence"
    assert len(lines.loc["R2", "geometry"].coords) == 3  # T3 (3 stops) beats T2 (2 stops)
    assert "R3" not in lines.index  # no trips: no geometry (reported by the caller)
