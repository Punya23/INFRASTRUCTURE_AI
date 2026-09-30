"""Build web/fixtures/city-index.json: one small row per city for the home page carousel and all-cities map.

Source: web/fixtures/invest/cities.json (balanced preset) + states.json. The invest fixtures are served by the API
function, not as static files, so the home page reads this flat copy instead. Re-run after `pipeline.invest export`.
"""
import json
from pathlib import Path

FIX = Path(__file__).resolve().parents[1] / "web" / "fixtures"
PRESET = "balanced"

cities = json.loads((FIX / "invest" / "cities.json").read_text())
states = {s["code"]: s["name"] for s in json.loads((FIX / "invest" / "states.json").read_text())}

rows = []
for c in cities:
    s = c["scores"][PRESET]  # KeyError on a city without the preset: fail loudly, never default a score
    best = s.get("best_area") or {}
    rows.append({
        "id": c["id"], "name": c["name"], "state": states[c["state"]],
        "lat": c["lat"], "lon": c["lon"], "score": s["score"], "pop": round(c["population"]),
        "metro": c["data"].get("metro_stations"), "rail": c["data"].get("rail_stations"),
        "best": [best["name"], best["score"]] if best.get("name") else None,
    })
rows.sort(key=lambda r: (-r["score"], -r["pop"], r["id"]))

(FIX / "city-index.json").write_text(json.dumps({"preset": PRESET, "as_of": cities[0]["fetched_at"], "cities": rows}, separators=(",", ":")))
print(f"{len(rows)} cities")
