"""Build web/brics-world.json: simplified country outlines for the BRICS page map.

Source: Natural Earth 110m (public domain), shipped as a test fixture inside pyogrio.
Not the Survey of India layer, so the page says so (invariant 6 covers official outputs; this is an illustration).
Run: cd ml && uv run python ../scripts/build_brics_map.py
"""
import json
from pathlib import Path

import geopandas as gpd
import pyogrio

# Natural Earth ISO-A3 (-99 for some, so match on name) for the ten members (as of 2025).
MEMBERS = {"India": "IND", "Brazil": "BRA", "Russia": "RUS", "China": "CHN", "South Africa": "ZAF",
           "Egypt": "EGY", "Ethiopia": "ETH", "Iran": "IRN", "United Arab Emirates": "ARE", "Indonesia": "IDN"}
W, H = 1000, 500  # equirectangular, lon -180..180, lat 84..-58 cropped below
LAT_TOP, LAT_BOT = 84.0, -58.0

def proj(x, y):
    return (x + 180) / 360 * W, (LAT_TOP - y) / (LAT_TOP - LAT_BOT) * H

path = Path(pyogrio.__file__).parent / "tests/fixtures/naturalearth_lowres/naturalearth_lowres.shp"
gdf = gpd.read_file(path)
gdf = gdf[gdf.name != "Antarctica"]

def ring(coords):
    pts = [proj(x, y) for x, y in coords]
    return "M" + "L".join(f"{x:.1f},{y:.1f}" for x, y in pts) + "Z"

out = []
for _, r in gdf.iterrows():
    geom = r.geometry.simplify(0.25, preserve_topology=True)
    polys = list(geom.geoms) if geom.geom_type == "MultiPolygon" else [geom]
    d = "".join(ring(p.exterior.coords) for p in polys if not p.is_empty and p.area > 0.4)
    if d:
        out.append({"n": r["name"], "m": MEMBERS.get(r["name"]), "d": d})

missing = set(MEMBERS) - {c["n"] for c in out if c["m"]}
assert not missing, f"members not found in source: {missing}"
Path(__file__).resolve().parents[1].joinpath("web/brics-world.json").write_text(json.dumps({"w": W, "h": H, "c": out}, separators=(",", ":")))
print(len(out), "countries")
