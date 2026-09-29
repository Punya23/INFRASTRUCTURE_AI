"""National-highway facts per H3 cell for the investor flow (spec §4): highway access and arterial
road length.

Only OSM-derived data is read (ADR-0014): nh_segments.parquet and osm_context_way_nodes.parquet;
the NHAI layers (nhai_*.parquet) are never opened here. Only operational segments count: a road
that is closed, being built or merely proposed gives no access today.

Arterial km count each road once. A divided road drawn as two ways counts as one road: NH by its
`eff_km`, every other arterial way by dual_carriageway_weights (0.5 for a carriageway with an
opposite partner within 30 m). Arterial km are NH, primary and secondary roads, and, because the
context file has no way tags, the `_link` slip roads of primary and secondary roads too (about 2% of
the km in the Pune region).
"""

from __future__ import annotations

import geopandas as gpd
import numpy as np
import pandas as pd
import pyproj
import shapely

from fields.national_highways.build import OUT
from fields.national_highways.normalize import dual_carriageway_weights
from pipeline.invest.facts import sum_by_cell
from pipeline.invest.geo import nearest_km
from pipeline.shared_layers import INDIA_CRS

_KINDS = ("nh_segment", "expressway_segment")
# Spacing of the points a highway is cut into when its km are spread over the cells it crosses. A
# discretisation step, not a policy number: a segment's km always add up to its `eff_km` whatever
# the step; a finer step only places them more exactly (a cell gains or loses at most one step of
# km per crossing).
_SAMPLE_M = 200
_GEOD = pyproj.Geod(ellps="WGS84")  # the same ellipsoid that gave nh_segments its length_km
_TO_METRES = pyproj.Transformer.from_crs("EPSG:4326", INDIA_CRS, always_xy=True)


def _open_segments() -> gpd.GeoDataFrame:
    seg = gpd.read_parquet(
        OUT / "nh_segments.parquet", columns=["kind", "status", "eff_km", "geometry"]
    )
    return seg[(seg["status"] == "operational") & seg["kind"].isin(_KINDS)]


def nh_access_km(centres: pd.DataFrame) -> pd.Series:
    """Km from each centre (lat, lon) to the nearest operational NH or expressway segment."""
    return nearest_km(centres, _open_segments().geometry)


def _nh_km_by_cell(res: int) -> pd.Series:
    """Operational NH `eff_km` (a divided road drawn as two ways counts once) spread over the cells
    each segment crosses: the segment is cut into equal parts of about `_SAMPLE_M`, and each part's
    midpoint carries its share. A segment of any length keeps its full km."""
    seg = _open_segments()
    lines = seg.geometry.to_crs(INDIA_CRS).to_numpy()
    parts = np.maximum(1, np.ceil(shapely.length(lines) / _SAMPLE_M)).astype(int)
    owner = np.repeat(np.arange(len(lines)), parts)  # the segment each point belongs to
    k = np.arange(parts.sum()) - np.repeat(np.cumsum(parts) - parts, parts)  # part number in it
    mid = shapely.line_interpolate_point(lines[owner], (k + 0.5) / parts[owner], normalized=True)
    mid = gpd.GeoSeries(mid, crs=INDIA_CRS).to_crs("EPSG:4326")
    return sum_by_cell(mid.x, mid.y, seg["eff_km"].to_numpy()[owner] / parts[owner], res)


def _divided_road_weights(way: np.ndarray, lon: np.ndarray, lat: np.ndarray) -> np.ndarray:
    """The length weight of the way each node belongs to: 0.5 for a carriageway of a divided road
    drawn as two ways, else 1. `way` is sorted, so a way's nodes are contiguous.

    The context file has no oneway tag, so every way is treated as one-way and
    dual_carriageway_weights pairs any two ways within its gap that run in opposite drawing
    directions. On the 2,244 ways of the Pune region, whose real tags are known, this differs from
    the tag-based weights by 0.7% of the km (2.5 km of 349).
    """
    way_no = pd.factorize(way)[0]
    has_line = np.bincount(way_no)[way_no] >= 2  # a way of one node has no length to weigh
    x, y = _TO_METRES.transform(lon[has_line], lat[has_line])
    lines = shapely.linestrings(np.column_stack([x, y]), indices=pd.factorize(way_no[has_line])[0])
    weight = np.ones(way_no.max() + 1 if len(way_no) else 0)
    weight[np.unique(way_no[has_line])] = dual_carriageway_weights(
        lines, np.ones(len(lines), dtype=bool), np.zeros(len(lines), dtype=bool)
    )
    return weight[way_no]


def _context_km_by_cell(res: int) -> pd.Series:
    """Primary and secondary roads that are not NH, and their `_link` slip roads, from
    osm_context_way_nodes.parquet (no way tags, so a link cannot be told from its road): the
    geodesic length of each pair of consecutive nodes of a way, times the way's weight (a divided
    road counts once, see `_divided_road_weights`), credited to the cell of its midpoint."""
    nodes = pd.read_parquet(
        OUT / "osm_context_way_nodes.parquet", columns=["way_id", "pos", "lon", "lat"]
    ).sort_values(["way_id", "pos"])
    way, lon, lat = (nodes[c].to_numpy() for c in ("way_id", "lon", "lat"))
    same = way[1:] == way[:-1]  # a pair is a segment only inside one way
    lon0, lat0, lon1, lat1 = lon[:-1][same], lat[:-1][same], lon[1:][same], lat[1:][same]
    _, _, metres = _GEOD.inv(lon0, lat0, lon1, lat1)
    weight = _divided_road_weights(way, lon, lat)[:-1][same]
    return sum_by_cell((lon0 + lon1) / 2, (lat0 + lat1) / 2, weight * metres / 1000, res)


def arterial_km_by_cell(res: int) -> pd.Series:
    """Arterial road km per H3 cell of resolution `res`: operational NH and expressway effective
    km, plus the other primary and secondary roads and their slip roads, each divided road counted
    once (see the module docstring). A cell with no such road is absent: OSM covers every cell, so
    the caller fills 0 there (road length is observed everywhere)."""
    return _nh_km_by_cell(res).add(_context_km_by_cell(res), fill_value=0.0)
