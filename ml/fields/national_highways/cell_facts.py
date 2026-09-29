"""National-highway facts per H3 cell for the investor flow (spec §4): highway access and arterial
road length.

Only OSM-derived data is read (ADR-0014): nh_segments.parquet and osm_context_way_nodes.parquet;
the NHAI layers (nhai_*.parquet) are never opened here. Only operational segments count: a road
that is closed, being built or merely proposed gives no access today.
"""

from __future__ import annotations

import geopandas as gpd
import numpy as np
import pandas as pd
import pyproj
import shapely

from fields.national_highways.build import OUT
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


def _context_km_by_cell(res: int) -> pd.Series:
    """Primary and secondary roads that are not NH (osm_context_way_nodes.parquet): the geodesic
    length of each pair of consecutive nodes of a way, credited to the cell of its midpoint.

    The file carries no oneway tag, so a divided road drawn as two ways counts both carriageways.
    """
    nodes = pd.read_parquet(
        OUT / "osm_context_way_nodes.parquet", columns=["way_id", "pos", "lon", "lat"]
    ).sort_values(["way_id", "pos"])
    way, lon, lat = (nodes[c].to_numpy() for c in ("way_id", "lon", "lat"))
    same = way[1:] == way[:-1]  # a pair is a segment only inside one way
    lon0, lat0, lon1, lat1 = lon[:-1][same], lat[:-1][same], lon[1:][same], lat[1:][same]
    _, _, metres = _GEOD.inv(lon0, lat0, lon1, lat1)
    return sum_by_cell((lon0 + lon1) / 2, (lat0 + lat1) / 2, metres / 1000, res)


def arterial_km_by_cell(res: int) -> pd.Series:
    """Arterial road km per H3 cell of resolution `res`: operational NH and expressway effective km
    plus primary and secondary roads that are not NH. A cell with no such road is absent: OSM covers
    every cell, so the caller fills 0 there (road length is observed everywhere)."""
    return _nh_km_by_cell(res).add(_context_km_by_cell(res), fill_value=0.0)
