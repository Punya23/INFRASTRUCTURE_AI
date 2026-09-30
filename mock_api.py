"""
Mock API server for the investor flow (port 8080).
Serves web/fixtures/invest/ data so the frontend works without the Go binary.
Replicates the Go API response shapes exactly.
Usage: python mock_api.py
"""
import gzip
import json
import math
import os
import re
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

FIXTURES = os.path.join(os.path.dirname(__file__), "web", "fixtures", "invest")


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_gz(path):
    with gzip.open(path, "rb") as f:
        return json.loads(f.read().decode("utf-8"))


# Load fixtures once at startup
META = load_json(os.path.join(FIXTURES, "meta.json"))
STATES = load_json(os.path.join(FIXTURES, "states.json"))
CITIES = load_json(os.path.join(FIXTURES, "cities.json"))

# Build indexes
CITIES_BY_ID = {c["id"]: c for c in CITIES}
CITIES_BY_STATE = {}
for c in CITIES:
    CITIES_BY_STATE.setdefault(c["state"], []).append(c)

# Factor units from meta
UNITS = {f["id"]: f["unit"] for f in META.get("factors", [])}
DEFAULT_PRESET = next((p["id"] for p in META.get("presets", []) if p.get("default")), "balanced")
PRESET_IDS = [p["id"] for p in META.get("presets", [])]


def flatten_city(c, preset):
    """Flatten a fixture city record into the Go API's cityView shape for a given preset."""
    ps = c.get("scores", {}).get(preset, {})
    return {
        "id": c["id"],
        "name": c["name"],
        "state": c["state"],
        "tier": c["tier"],
        "population": round(c.get("population", 0)),
        "score": ps.get("score", 0),
        "access": ps.get("access"),
        "momentum": ps.get("momentum"),
        "coverage": ps.get("coverage", 1.0),
        "confidence": ps.get("confidence", 0),
        "drivers": ps.get("drivers", []),
        "gaps": ps.get("gaps", []),
        "best_area": ps.get("best_area", {}),
        "source": c.get("source", ""),
        "source_ref": c.get("source_ref", ""),
        "fetched_at": c.get("fetched_at", ""),
        "license": c.get("license", ""),
    }


def flatten_city_detail(c, preset):
    """Full city detail: cityView + extra fields."""
    view = flatten_city(c, preset)
    view["aliases"] = c.get("aliases", [])
    view["lat"] = c.get("lat", 0)
    view["lon"] = c.get("lon", 0)
    view["area_km2"] = c.get("area_km2", 0)
    view["cells"] = c.get("cells", 0)
    view["factors"] = c.get("factors", {})
    view["data"] = c.get("data", {})
    return view


def ranked(cities, preset):
    """Sort cities by preset score descending, then population descending, then id ascending."""
    return sorted(cities, key=lambda c: (
        -c.get("scores", {}).get(preset, {}).get("score", 0),
        -c.get("population", 0),
        c.get("id", ""),
    ))


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        print(f"[mock-api] {self.address_string()} - {fmt % args}")

    def send_json(self, data, status=200):
        body = json.dumps(data, allow_nan=False, default=str).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(body)

    def send_error_json(self, code, message, status):
        self.send_json({"error": {"code": code, "message": message}}, status)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")
        qs = parse_qs(parsed.query)

        def qp(name, default=None):
            vals = qs.get(name)
            return vals[0] if vals else default

        def preset():
            p = qp("preset")
            if p is None:
                return DEFAULT_PRESET
            if p in PRESET_IDS:
                return p
            return None

        # ── GET /v1/health ────────────────────────────────────────────────
        if path == "/v1/health":
            self.send_json({"status": "ok", "as_of": META.get("as_of", "")})
            return

        # ── GET /v1/meta ──────────────────────────────────────────────────
        if path == "/v1/meta":
            self.send_json(META)
            return

        # ── GET /v1/states ────────────────────────────────────────────────
        if path == "/v1/states":
            self.send_json({"as_of": META.get("as_of", ""), "states": STATES})
            return

        # ── GET /v1/states/{CODE}/cities ──────────────────────────────────
        m = re.fullmatch(r"/v1/states/([A-Z]{2})/cities", path)
        if m:
            code = m.group(1)
            p = preset()
            if p is None:
                self.send_error_json("bad_request", f"preset must be one of {', '.join(PRESET_IDS)}", 400)
                return
            limit = int(qp("limit", 5))
            state_cities = CITIES_BY_STATE.get(code)
            if not state_cities:
                self.send_error_json("not_found", f"state {code} not found", 404)
                return
            cities = ranked(state_cities, p)[:limit]
            cards = [{"rank": i + 1, **flatten_city(c, p)} for i, c in enumerate(cities)]
            self.send_json({"state": code, "preset": p, "total": len(state_cities), "cities": cards})
            return

        # ── GET /v1/cities?q=...  (search) ────────────────────────────────
        if path == "/v1/cities":
            q = (qp("q") or "").strip().lower()
            limit = int(qp("limit", 8))
            if len(q) < 2:
                self.send_error_json("bad_request", "q must be at least 2 characters", 400)
                return
            hits = []
            for c in CITIES:
                matched = None
                names = [c["name"]] + c.get("aliases", [])
                for name in names:
                    if q in name.lower():
                        is_prefix = name.lower().startswith(q)
                        if matched is None or (is_prefix and not matched[1]):
                            matched = (name, is_prefix)
                if matched:
                    hits.append({
                        "id": c["id"], "name": c["name"], "state": c["state"],
                        "tier": c["tier"], "population": round(c.get("population", 0)),
                        "matched": matched[0], "_prefix": matched[1],
                    })
            # Sort: prefix matches first, then by population desc
            hits.sort(key=lambda h: (not h["_prefix"], -h["population"], h["id"]))
            for h in hits:
                del h["_prefix"]
            self.send_json({"cities": hits[:limit]})
            return

        # ── GET /v1/cities/{id}/areas ─────────────────────────────────────
        m = re.fullmatch(r"/v1/cities/([a-z0-9-]{2,64})/areas", path)
        if m:
            city_id = m.group(1)
            p = preset()
            if p is None:
                self.send_error_json("bad_request", f"preset must be one of {', '.join(PRESET_IDS)}", 400)
                return
            limit = int(qp("limit", 500))
            gz_path = os.path.join(FIXTURES, "assets", f"{city_id}.json.gz")
            if not os.path.exists(gz_path):
                self.send_error_json("not_found", f"city {city_id!r} not found", 404)
                return
            raw = load_gz(gz_path)
            # The .gz file has "areas" as a FeatureCollection with features that have per-preset data
            areas_fc = raw.get("areas")
            if not areas_fc or areas_fc.get("type") != "FeatureCollection":
                self.send_error_json("not_found", f"no areas for {city_id!r}", 404)
                return
            features = areas_fc.get("features", [])
            # Sort by preset score descending
            def cell_score(f):
                return f.get("properties", {}).get("sc", {}).get(p, 0)
            features_sorted = sorted(features, key=lambda f: (-cell_score(f), -f.get("properties", {}).get("pop", 0)))
            # Build response features with flattened preset data
            out_features = []
            for rank, f in enumerate(features_sorted[:limit], 1):
                props = f.get("properties", {})
                d_raw = props.get("d", {}).get(p, [])
                g_raw = props.get("g", {}).get(p, [])
                drivers = [{"factor": x["factor"], "points": x["value"], "value": props.get("f", {}).get(x["factor"]), "unit": UNITS.get(x["factor"], "")} for x in d_raw]
                gaps = [{"factor": x["factor"], "subscore": x["value"], "value": props.get("f", {}).get(x["factor"]), "unit": UNITS.get(x["factor"], "")} for x in g_raw]
                out_features.append({
                    "type": "Feature",
                    "geometry": f.get("geometry"),
                    "properties": {
                        "id": props.get("id"),
                        "name": props.get("name"),
                        "pop": props.get("pop", 0),
                        "elig": props.get("elig", False),
                        "bus_stops": props.get("bus_stops"),
                        "rank": rank,
                        "score": props.get("sc", {}).get(p, 0),
                        "access": props.get("ac", {}).get(p),
                        "coverage": props.get("cov", 1.0),
                        "confidence": props.get("conf", 0),
                        "f": props.get("f", {}),
                        "s": props.get("s", {}),
                        "d": drivers,
                        "g": gaps,
                        "source": raw.get("source", ""),
                        "source_ref": props.get("source_ref", ""),
                        "fetched_at": raw.get("fetched_at", ""),
                        "license": raw.get("license", ""),
                    }
                })
            self.send_json({"type": "FeatureCollection", "features": out_features})
            return

        # ── GET /v1/cities/{id}/assets ────────────────────────────────────
        m = re.fullmatch(r"/v1/cities/([a-z0-9-]{2,64})/assets", path)
        if m:
            city_id = m.group(1)
            gz_path = os.path.join(FIXTURES, "assets", f"{city_id}.json.gz")
            if not os.path.exists(gz_path):
                self.send_error_json("not_found", f"city {city_id!r} not found", 404)
                return
            raw = load_gz(gz_path)
            layers_param = qp("layers")
            want = set(layers_param.split(",")) if layers_param else {"stations", "bus_stops", "highways", "toll_plazas"}
            out = {"source": raw.get("source", ""), "fetched_at": raw.get("fetched_at", ""), "license": raw.get("license", "")}
            if "stations" in want:
                out["stations"] = raw.get("stations")
            if "bus_stops" in want:
                out["bus_stops"] = raw.get("bus_stops")
                out["bus_source"] = raw.get("bus_source")
            if "highways" in want:
                out["highways"] = raw.get("highways")
            if "toll_plazas" in want:
                out["toll_plazas"] = raw.get("toll_plazas")
            self.send_json(out)
            return

        # ── GET /v1/cities/{id}/compare ───────────────────────────────────
        m = re.fullmatch(r"/v1/cities/([a-z0-9-]{2,64})/compare", path)
        if m:
            city_id = m.group(1)
            city = CITIES_BY_ID.get(city_id)
            if not city:
                self.send_error_json("not_found", f"city {city_id!r} not found", 404)
                return
            p = preset()
            if p is None:
                self.send_error_json("bad_request", f"preset must be one of {', '.join(PRESET_IDS)}", 400)
                return
            scope = qp("scope", "")
            limit = int(qp("limit", 5))
            tier = city.get("tier", "")

            if not scope:
                scope = "metros" if tier == "metro" else "peers"

            scope_filters = {
                "metros": lambda c: c.get("tier") == "metro",
                "peers": lambda c: c.get("tier") == tier,
                "state": lambda c: c.get("state") == city.get("state"),
                "india": lambda c: True,
            }
            in_scope = scope_filters.get(scope, scope_filters["peers"])
            pool = [c for c in CITIES if c["id"] != city_id and in_scope(c)]
            pool_sorted = ranked(pool, p)

            base_score = city.get("scores", {}).get(p, {}).get("score", 0)
            base_factors = city.get("factors", {})

            # Rank: 1 + count of cities scoring higher than base
            base_rank = 1 + sum(1 for c in pool if c.get("scores", {}).get(p, {}).get("score", 0) > base_score)

            others = []
            for rank_idx, c in enumerate(pool_sorted[:limit], 1):
                c_score = c.get("scores", {}).get(p, {}).get("score", 0)
                c_factors = c.get("factors", {})
                # Compute factor deltas (other subscore - base subscore)
                deltas = []
                for fid in UNITS:
                    base_sub = base_factors.get(fid, {}).get("subscore", 0) or 0
                    other_sub = c_factors.get(fid, {}).get("subscore", 0) or 0
                    d = round(other_sub - base_sub, 1)
                    if d != 0:
                        deltas.append({"factor": fid, "delta": d, "base": base_sub, "other": other_sub})
                better = sorted([x for x in deltas if x["delta"] > 0], key=lambda x: -x["delta"])[:2]
                worse = sorted([x for x in deltas if x["delta"] < 0], key=lambda x: x["delta"])[:2]

                actual_rank = 1 + sum(1 for x in pool if x.get("scores", {}).get(p, {}).get("score", 0) > c_score)
                others.append({
                    "rank": actual_rank, "id": c["id"], "name": c["name"],
                    "state": c["state"], "tier": c.get("tier", ""),
                    "score": c_score, "delta": round(c_score - base_score, 1),
                    "better": better, "worse": worse,
                })

            self.send_json({
                "base": {"rank": base_rank, **flatten_city(city, p)},
                "preset": p, "scope": scope,
                "total": len(pool),
                "base_rank": base_rank,
                "others": others,
            })
            return

        # ── GET /v1/cities/{id} ───────────────────────────────────────────
        m = re.fullmatch(r"/v1/cities/([a-z0-9-]{2,64})", path)
        if m:
            city_id = m.group(1)
            city = CITIES_BY_ID.get(city_id)
            if not city:
                self.send_error_json("not_found", f"city {city_id!r} not found", 404)
                return
            p = preset()
            if p is None:
                self.send_error_json("bad_request", f"preset must be one of {', '.join(PRESET_IDS)}", 400)
                return
            self.send_json(flatten_city_detail(city, p))
            return

        self.send_error_json("not_found", "no such endpoint", 404)


if __name__ == "__main__":
    server = HTTPServer(("localhost", 8080), Handler)
    print(f"Mock investor API listening on http://localhost:8080")
    print(f"Default preset: {DEFAULT_PRESET}, presets: {PRESET_IDS}")
    print("Press Ctrl+C to stop.")
    server.serve_forever()
