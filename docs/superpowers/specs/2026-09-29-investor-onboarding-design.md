# Investor onboarding — where should I invest? (design)

- Date: 2026-09-29 · Status: approved by the user on 2026-09-29 (returns → none, backend → Go without DB, login → none)
- Related: README §2, §9, §10, §15 · ADR-0003, ADR-0004, ADR-0006, ADR-0011, ADR-0012, ADR-0014 · skill `add-api-endpoint`

## 1. Goal

A visitor who wants to put money into property picks a state, sees the **top 5 cities** in it with the reasons, opens a city and sees its **best areas** on a map, and sees **other cities compared** in a side panel. Every number comes from observed infrastructure data and is explained. No returns, price or forecast figures appear anywhere.

**Flow**

1. **Landing** (`web/invest/index.html`) — what this is, one CTA.
2. **Start** (`start.html`, three light steps) — home state → where to invest (a state, or search a city) → what matters most (preset chips, default Balanced). Answers saved in the browser.
3. **State result** (`state.html?s=MH`) — top 5 cities: rank, score, three "why" chips with numbers, best area, "watch-outs".
4. **City** (`city.html?c=pune`) — hex-grid heat map, ranked best areas, layer toggles (stations, bus stops, highways, tolls) and a **compare panel** on the right.

**Persona and framing** — README §2 "Investor, homebuyer": a growth outlook that is informational, never advice (README §15). Growth is shown per H3 area (≈5 km²), never per parcel.

## 2. Decisions and non-goals

| Decision | Choice | Why |
|---|---|---|
| "Returns %" | **None.** Rank by an explainable Access + Momentum score with drivers; compare cities by per-factor differences | ADR-0003 (Accepted), README §13 "Won't: price forecasting", AGENTS invariants 3 and 4. No source exists to compute returns. A past-only official price index (RBI HPI) is a possible follow-up after a license check (skill `add-data-source`) |
| Backend | **Go stdlib API** (ADR-0006) serving pipeline-exported JSON; no database yet | Nothing writes data. Postgres arrives with M0 and the store package swaps behind the same handlers |
| Login | **None.** State and preset live in `localStorage` | Accounts mean personal data, an ADR and DPDP work (invariant 5) |
| Web stack | Static HTML + ES modules under `web/invest/`, existing `i18n.js` | Matches the shipped `web/`; the Next.js shell is M0 |
| Landing location | New pages in `web/invest/`, linked from the current `web/index.html` nav | Does not overwrite the citizen explorer other people own |

**Non-goals (v1):** returns, price, rent or yield numbers · accounts and saved lists · pipeline projects in the score (M3 brings cited events) · bus in the score · parcel or street level · vector tiles, PostGIS · state or country outlines on maps (ADR-0007) · policymaker views.

## 3. Architecture

```
data/raw + data/processed ──► ml/pipeline/invest (Python) ──► web/fixtures/invest/*.json
                                                                  │  loaded at start
                                                                  ▼
web/invest/*.html + js  ◄── fetch /v1/... ◄── api (Go, net/http, in-memory store)
```

Three parallel tracks, disjoint files:

| Track | Owns | Delivers |
|---|---|---|
| **D — pipeline** | `config/scoring.yaml`, `config/states.yaml`, `ml/pipeline/invest/`, `ml/fields/{national_highways,public_transport}/cell_facts.py`, `ml/tests/test_invest_*.py`, `web/fixtures/invest/` | Cities, areas, scores, drivers, assets as fixtures |
| **A — API** | `api/` (`openapi.yaml`, `cmd/api`, `internal/{http,store}`, `testdata/`), `.claude/launch.json` (api entry) | Endpoints in §7, tests |
| **W — web** | `web/invest/`, `inv.*` keys in `web/locales/{en,hi,kn}.json`, one nav link in `web/index.html` | The four pages in §1 |

Track A writes `api/testdata/invest/` from the §6 contract with `source: "synthetic-test"` on every record (never shipped, never served in production) so W can build before D finishes. Integration switches the data directory to `web/fixtures/invest/`.

## 4. Scoring model (explainable, config-weighted — ADR-0003)

All parameters live in `config/scoring.yaml`; **every number carries a comment with its basis** (a norm, a source, or "team judgment, 2026-09-29"). Loaded by the pipeline only; the API and web read exported values.

**Factors** (five, all from sources that cover every city in India):

| id | group | raw value (per area) | unit | better | source |
|---|---|---|---|---|---|
| `nh_access` | access | distance from area centre to the nearest operational NH or expressway | km | lower | `nh_segments.parquet` (OSM-derived) |
| `rail_access` | access | distance to the nearest heavy or suburban rail station | km | lower | OSM `railway=station\|halt` |
| `metro_access` | access | distance to the nearest metro, monorail or light-rail station | km | lower | OSM `station=subway\|light_rail\|monorail` ∪ GTFS metro stops (HMRL, BMRCL, CMRL) |
| `road_strength` | access | trunk + primary + secondary road length per km² inside the area | km/km² | higher | OSM ways. Measures network capacity, **not pavement condition** — copy must say so |
| `built_up_growth` | momentum | change in built-up share 2000 → 2020 | pp | higher | GHSL built-up surface, 1 km |

Bus stops are **shown, not scored**: GTFS exists for 5 cities only and a factor that exists for some cities breaks comparability. They appear as a map layer, a per-area count (`bus_stops`, null where no feed) and `data.bus` on the city.

**Sub-score** = piecewise-linear map of the raw value to 0–100 through knots in config (`bands`). Initial knots (verify against the measured national distribution and record the percentiles in the config comment):

| factor | knots (value → score) |
|---|---|
| `nh_access` | 0→100, 2→90, 5→70, 10→40, 25→0 |
| `rail_access` | 0→100, 1→90, 3→65, 8→25, 15→0 |
| `metro_access` | 0→100, 1→90, 2→70, 5→30, 10→0 |
| `road_strength` | 0→0, 0.3→30, 1→65, 2→90, 3→100 |
| `built_up_growth` | 0→0, 1→30, 3→60, 8→90, 15→100 (re-anchored on the measured distribution — p50 0.9, p90 3.9, p99 12.1 pp; the initial 3/10/25/40 knots put 91.5 % of areas below the watch-out line) |

**Presets** (weights sum to 1, checked by a test): `balanced` 0.25 / 0.15 / 0.15 / 0.15 / 0.30 · `commuter` 0.10 / 0.25 / 0.30 / 0.10 / 0.25 · `highway` 0.45 / 0.05 / 0 / 0.20 / 0.30 · `growth` 0.15 / 0.10 / 0.10 / 0.10 / 0.55 (order: nh, rail, metro, roads, growth).

**Score** (area, preset p) = Σ w_f·s_f ÷ Σ w_f over factors **observed** in that area. A missing factor is dropped and the weights renormalised; it is **never scored as zero** (invariant 2). `coverage` = observed weight ÷ total weight. `access` = the same mean over the access group only; `momentum` = the `built_up_growth` sub-score. `confidence` = 0.8 × coverage (0.8 = community and modelled sources, team judgment).

**Drivers** — per area and preset: the top 3 factors by contribution `w_f·s_f ÷ Σ w_obs` (points that sum to the score) with sub-score ≥ 50, and up to 2 **gaps** (sub-score < 40, largest `w·(100−s)`). Each carries the raw value and unit. "Why" text is a UI template filled with these numbers — **no LLM writes any sentence**.

**City score** (preset p) = population-weighted mean of its areas' scores (WorldPop 2020). City-level fields follow the same weighting so they reconcile with the score:
- `factors[f].value` = population-weighted **median** raw value; `share` = share of residents inside the factor's headline band (`headline_band_km`: 2 km rail and metro, 10 km NH; null for roads and growth); `subscore` = population-weighted mean of the areas' sub-scores (areas where `f` is observed).
- `drivers` and `gaps` = population-weighted mean of each factor's per-area **points**, so city drivers sum to the city score; same thresholds as areas.
- `best_area` = the highest-scoring **eligible** area (below).

**Ranking eligibility** (`elig`): an area is eligible for "best area" lists when its population ≥ `best_area_min_population` (5,000 ≈ 1,000 people/km², a built-up neighbourhood; team judgment). If fewer than 3 areas qualify, all areas are eligible. Ineligible areas still draw on the map.

**Sensitivity summary** (definition of done for scoring changes): re-rank cities under 200 random ±30 % weight perturbations per preset; report top-5 overlap per state and rank correlation between presets. Commit as a table in ADR-0015.

## 5. Cities and areas

**City = urban centre ∩ state.** Basis: UN Degree of Urbanisation (2020) urban centre — contiguous WorldPop 2020 1 km cells with ≥ 1,500 people/km², 8-connected — cut at state borders so a state list contains its own cities (Gurugram is Haryana's, not Delhi's). Keep pieces with ≥ 100,000 people (config). GeoNames populations are **not** used (Kallakurichi shows 1.68 M; Delhi is split into Rohini and Narela); GeoNames supplies names and centres only.

- **Name and centre:** the largest GeoNames place inside the piece. `name_overrides` in config (geonameid → name, with a reason) fixes the few cases where the largest place is not the investor's name (e.g. Gurugram). The pipeline prints every piece holding two or more places ≥ 100 k for review; it never fixes them silently.
- **Aliases:** other GeoNames places ≥ 100 k inside the piece, so "Thane" finds Mumbai's region, "Pimpri-Chinchwad" finds Pune.
- **Id:** slug of the name; on a collision every colliding city gets `-<state code lower>` (`aurangabad-mh`), then `-2`. Deterministic.
- **Tier:** `metro` ≥ 2.5 M, `large` ≥ 1 M, else `mid` (config, team judgment).
- **State assignment:** DataMeet state polygons, for point-in-polygon only. They are never drawn (ADR-0007). State codes: ISO 3166-2:IN in `config/states.yaml`. All 36 states and UTs are listed; `city_count` may be 0.

**Areas** — H3 resolution 7 (≈5.2 km², matches the 1 km rasters; no false precision). Cells whose centre lies within the piece buffered by `buffer_rings` (3) rings, keeping cells with WorldPop population ≥ `min_area_population` (1,000 — empty farmland is not an "area"). Two cities may share cells; scores are properties of the cell.

**Area name** — from OSM `place` nodes (`name:en` else `name`): inside the cell, ranked suburb > neighbourhood > quarter > village > town > hamlet, then closest to the cell centre; else the nearest place within 2.5 km; else `null` and the UI shows "Area near {place}". The top-N list shows the best cell per name.

## 6. Fixture contract — `web/fixtures/invest/`

Each file ≤ 5 MB and the directory ≤ 25 MB on disk (if over, raise `min_population` and record why). `areas/` and `assets/` files are **gzip** (`.geojson.gz`, `.json.gz`, level 9); the API store also accepts the plain name, which the synthetic test data uses. Every record carries provenance (invariant 1): `source`, `source_ref`, `fetched_at`, `license`, `confidence`. In area files the provenance sits once on the FeatureCollection (`source`, `fetched_at`, `license`) with `source_ref` (= the H3 id) and `conf` per feature; the API copies the collection-level fields into every feature it serves. Coordinates rounded to 4 decimals. Scores, sub-scores and raw values are numbers with one decimal. Counts (`cells`, `city_count`, `data.bus.stops`, `data.metro_stations`, `data.rail_stations`) are JSON integers; `population`, `pop` and `bus_stops` are plain numbers. The API refuses to start on unknown fields, missing required numbers or a preset missing from `d`/`g`, so the exporter writes exactly these fields.

| File | Content |
|---|---|
| `meta.json` | `schema_version` (1), `as_of`, `grid` (copy of `config/scoring.yaml` `grid`: `h3_res`, `buffer_rings`, `min_area_population`, `best_area_min_population`), `factors` (id, group, unit, better, `headline_band_km`, `bands`), `presets` (id, weights, `default`), `tiers` (copy of `cities.tiers`: `metro_min_population`, `large_min_population`), `sources` (id, name, license, attribution), `disclaimer` |
| `states.json` | `[{code, name, city_count}]`, all 36 |
| `cities.json` | `[city]` — see below |
| `areas/<city>.geojson.gz` | FeatureCollection of H3 cells |
| `assets/<city>.json.gz` | `stations`, `bus_stops`, `highways`, `toll_plazas` |

```jsonc
// cities.json[i]
{
  "id": "pune", "name": "Pune", "state": "MH", "aliases": ["Pimpri-Chinchwad"],
  "lat": 18.5196, "lon": 73.8553, "population": 6100000, "area_km2": 850.0, "tier": "metro", "cells": 143,
  "factors": {                                   // city summary, all five factors
    "metro_access": {"value": 6.5, "unit": "km", "share": 0.22, "band_km": 2, "subscore": 30.0},
    "built_up_growth": {"value": 24.0, "unit": "pp", "share": null, "band_km": null, "subscore": 88.0}
  },
  "scores": {                                    // one entry per preset id
    "balanced": {
      "score": 71.4, "access": 66.0, "momentum": 88.0, "coverage": 1.0, "confidence": 0.8,
      "drivers": [{"factor": "built_up_growth", "points": 26.4, "value": 24.0, "unit": "pp", "share": null, "band_km": null}],
      "gaps":    [{"factor": "metro_access", "subscore": 30.0, "value": 6.5, "unit": "km", "share": 0.22, "band_km": 2}],
      "best_area": {"id": "87…", "name": "Hinjewadi", "score": 84.2}
    }
  },
  "data": {"bus": {"operator": "PMPML", "tier": "secondary", "stops": 6713}, "metro_stations": 12, "rail_stations": 9},
  "source": "osm+worldpop2020+ghsl2020+gtfs", "source_ref": "city:pune", "fetched_at": "2026-09-29",
  "license": "ODbL-1.0; CC-BY-4.0", "confidence": 0.8
}
```

```jsonc
// areas/pune.geojson.gz — {"type": "FeatureCollection", "city": "pune", "source": "osm+worldpop2020+ghsl2020",
//   "fetched_at": "2026-09-29", "license": "ODbL-1.0; CC-BY-4.0", "features": [...]}, sorted by balanced score
{"type": "Feature", "geometry": {"type": "Polygon", "coordinates": [[[73.71,18.59], …]]},
 "properties": {
   "id": "8760…", "name": "Hinjewadi", "pop": 48210, "elig": true, "bus_stops": 31,
   "f": {"nh_access": 1.8, "rail_access": 9.4, "metro_access": 3.1, "road_strength": 2.2, "built_up_growth": 41.0},  // raw, null = unobserved
   "s": {"nh_access": 88.0, "rail_access": 22.0, "metro_access": 65.0, "road_strength": 92.0, "built_up_growth": 100.0},  // sub-scores, null = unobserved
   "sc": {"balanced": 78.1, "commuter": 70.3, "highway": 85.0, "growth": 80.2},
   "ac": {"balanced": 72.0, "commuter": 66.5, "highway": 79.0, "growth": 68.0},
   "d": {"balanced": [["built_up_growth", 30.0], ["road_strength", 13.8]], "commuter": […], "highway": […], "growth": […]},   // drivers for EVERY preset: factor, points (top 3)
   "g": {"balanced": [["rail_access", 22.0]], "commuter": […], "highway": […], "growth": […]},   // gaps for EVERY preset: factor, sub-score (up to 2)
   "cov": 1.0, "conf": 0.8, "source_ref": "h3:8760…"}}
```

`assets/<city>.json`: `{"city", "source", "fetched_at", "license", "stations": FeatureCollection<Point{name, mode: metro|rail, source}>, "bus_stops": FeatureCollection<Point{name}> | null, "bus_source": {operator, tier, license, fetched_at} | null, "highways": FeatureCollection<(Multi)LineString{ref, status, kind}> (simplified, bounding box of the areas + 5 km), "toll_plazas": FeatureCollection<Point{name}>}`. NHAI-derived numbers appear **only as aggregates** (ADR-0014); geometry is OSM.

## 7. API contract — `api/openapi.yaml` is the source of truth

JSON over HTTP. Errors are always `{"error": {"code": "...", "message": "..."}}` with codes `bad_request` (400), `not_found` (404), `rate_limited` (429), `timeout` (503), `internal` (500); no internal detail leaks. `preset` ∈ `meta.presets` (default = the preset marked `default`); unknown value → 400. `limit` bounds are enforced per endpoint (out of range → 400, never clamped silently).

| Method · path | Query | Returns |
|---|---|---|
| `GET /healthz` | — | `{"status":"ok","as_of":"…"}` |
| `GET /v1/meta` | — | `meta.json` |
| `GET /v1/states` | — | `{"as_of","states":[{code,name,city_count}]}` |
| `GET /v1/states/{code}/cities` | `preset`, `limit` 1–20 (default 5) | `{"state","preset","total","cities":[ranked city cards]}` — card = rank, id, name, tier, population, `score`, `access`, `momentum`, `coverage`, `confidence`, `drivers`, `gaps`, `best_area`, provenance. Unknown code → 404 |
| `GET /v1/cities` | `q` (≥ 2 chars, matches name and aliases, case-insensitive, prefix first), `limit` 1–20 (default 8) | `{"cities":[{id,name,state,tier,population,matched}]}` |
| `GET /v1/cities/{id}` | `preset` | one city: everything in the card except `rank`, plus `state`, `factors`, `aliases`, `lat`, `lon`, `area_km2`, `cells`, `data`, provenance |
| `GET /v1/cities/{id}/areas` | `preset`, `limit` 1–1000 (default 500) | GeoJSON FeatureCollection sorted by that preset's score. Feature `properties` = `{id, name, pop, elig, bus_stops, rank, score, access, coverage, confidence, f, s, d, g, source, source_ref, fetched_at, license}` where `rank` runs over all cells, `score`/`access` are for the requested preset, `d` = `[{factor, points, value, unit}]` and `g` = `[{factor, subscore, value, unit}]` (values taken from `f`), and `source`, `fetched_at`, `license` are copied from the collection |
| `GET /v1/cities/{id}/assets` | `layers` ⊆ `stations,bus_stops,highways,toll_plazas` (default all) | the requested collections, `bus_source` |
| `GET /v1/cities/{id}/compare` | `preset`, `scope` ∈ `metros,peers,state,india`, `limit` 1–10 (default 5) | `{"base":{card},"preset","scope","total","base_rank","others":[{rank,id,name,state,tier,score,delta,better:[{factor,delta,base,other}],worse:[…]}]}` |

- `compare` default scope: `metros` when the base city is a metro, else `peers` (same tier, whole India). `others` excludes the base city, is sorted by score descending (better and worse cities both appear), and `delta` = other − base. `better` and `worse` hold up to 2 sub-score differences each (`base`/`other` are the two sub-scores) — the "why" of the delta. `base_rank` is the base city's rank among the compared set including itself.
- **Robustness:** ids and codes are validated with fixed patterns (`^[A-Z]{2}$`, `^[a-z0-9-]{2,64}$`) and looked up in memory — never used to build paths. `http.Server` timeouts, per-request context timeout 5 s, per-IP fixed-window rate limit (default 120 req/min, env-tunable), CORS allow-list from env (default `http://localhost:8765`), `X-Content-Type-Options: nosniff`, `Cache-Control: public, max-age=300` on data routes. Data is loaded once at start; a missing or malformed fixture stops start-up with a clear error (fail closed).
- **Flags:** `-addr` (default `:8080`), `-data` (default `../web/fixtures/invest`).
- The Go store holds no scoring logic; scores, sub-scores and drivers come from the fixtures. A test asserts every area's driver points sum to its stored score (±0.1) and every stored score matches the weighted mean of its sub-scores under `meta.presets` — this is the parity check between the Python scorer and what is served.

## 8. Web (`web/invest/`)

- **Files:** `index.html`, `start.html`, `state.html`, `city.html`, `invest.css` (tokens mirror `web/index.html`: canvas `#F7F6F2`, teal `#0E5A66`, saffron `#E08A1E`, Inter, Noto per script), `js/{config,api,prefs,format,ui}.js` as ES modules. `config.js`: API base is `http://localhost:8080` when the page is served from port 8765, else same origin.
- **Landing:** headline that promises evidence, not gains ("Invest where infrastructure already delivers"); CTA "Find where to invest"; a live sample card from `/v1/states/MH/cities?limit=3`; how it works (3 steps); what is measured (Access: highways, metro and rail, road network · Momentum: built-up growth); sources and licenses; "what this is not" (not forecasts, not advice); footer with attribution. A tile-grid or hex motif instead of an India outline (ADR-0007).
- **Start:** step 1 searchable state grid (all 36, with city counts); step 2 "In {home state}" / "Another state" / city search box (`/v1/cities?q=`); step 3 preset chips with one-line meanings. Skippable, keyboard-operable, back button works; saved to `localStorage` (`invest.prefs`) inside try/catch; the URL is always the source of truth on later pages.
- **State result:** up to 5 cards (fewer states show fewer, with the text "Only N cities above 1 lakh people"; 0 shows an honest empty state). Card: rank, name, score ring, Access and Momentum bars, three "why" chips (`drivers`), one "watch-out" (`gaps`), best area, "Explore {city}". Preset chips re-fetch. Aside: "Other metros to compare" from `/compare` of the top city.
- **City:** MapLibre GL 4.7.1 (as `nh-explorer.html`) with the OpenFreeMap positron style, falling back to a plain style if it fails to load; hex fill coloured by the preset score on a 5-step sequential ramp with legend; click or hover → popup with name, score, drivers, gaps, bus stops; layer toggles lazy-load `/assets`; ranked "Best areas" list (top 10 features with `elig`, best cell per name) is the keyboard and screen-reader equivalent of the map; **compare panel** on the right (stacked below on phones) with scope switch, delta chips and "+22 metro access · −11 growth" reasons, each row a link to that city with the same preset. Header: population, tier, built-up growth, data flags ("Bus data: PMPML" or "No bus feed for this city — bus stops not scored").
- **Copy rules:** strings in `web/locales/{en,hi,kn}.json` under `inv.*` (other locales fall back to English via `i18n.js`); numbers formatted per locale; a persistent line "Scores describe existing infrastructure and past growth. They are not forecasts, price predictions or financial advice." on every result page; the words return(s), ROI, yield, profit, appreciation, guaranteed never appear in `web/invest/` or `inv.*` keys (a test enforces it).
- **Quality bar:** responsive from 360 px, WCAG AA contrast, visible focus, `prefers-reduced-motion`, no layout shift while data loads (skeletons), every fetch has a timeout and an error state with retry — never a blank page.

## 9. Invariants check

| # | Invariant | How it holds |
|---|---|---|
| 1 | Provenance | Every city, area and asset record has `source`, `source_ref`, `fetched_at`, `license`, `confidence` |
| 2 | Fail closed | Unobserved factor is dropped and shown in `coverage`, never zero; malformed fixtures stop the API; 4xx on bad input |
| 3 | AI never originates facts | No LLM in this feature; "why" text is templated from stored numbers |
| 4 | Explainable analytics | Config-weighted sums, drivers stored, sensitivity summary published |
| 5 | Privacy | No accounts, no personal data, preferences stay in the browser |
| 6 | Official boundaries | No outline is drawn; DataMeet polygons are used only for point-in-polygon |
| 7 | Licenses before data | OSM (ODbL, attribution and share-alike on the fixtures), WorldPop and GHSL (CC BY 4.0), GeoNames (CC BY 4.0), GTFS per feed manifest; attribution in `meta.json` and every page footer |
| 8 | Field- and city-agnostic core | City names only in config and data; field facts live in `ml/fields/<field>/cell_facts.py`; shared code sees factor ids only |
| 9 | Idempotent pipelines | `python -m pipeline.invest all` re-runs safely and rewrites the fixtures deterministically |
| 10 | Contract-first API | `api/openapi.yaml` written first; handlers tested against its examples |
| 11 | Swappable AI | Not applicable (no AI) |
| 12 | Lean stack | Go stdlib only, no new Python dependency (h3, duckdb, rasterio, shapely, geopandas are installed), no new service, no datastore |

## 10. Testing and acceptance

- **Pipeline (pytest):** sub-score interpolation at every knot and outside the range · weights sum to 1 · missing factor renormalises and lowers `coverage` (never zero) · driver points sum to the score · city score is the population-weighted mean · urban-centre labelling on a synthetic grid, including the state cut · slug collisions · fixture size and provenance keys · banned-word check on `web/invest/` and `inv.*` locale keys.
- **Data spot checks** (run when the real fixtures exist): Maharashtra returns ≥ 5 cities including Mumbai, Pune, Nagpur and Nashik; the Pune areas include at least three of Hinjewadi, Kharadi, Hadapsar, Baner, Wakad, Wagholi; Haryana has a Gurugram-area city; a state whose largest urban centre is under 100,000 people returns `total: 0` (Goa: its largest contiguous zone at 1,500 people/km² holds about 82,000, so the first real run has none — the original "Goa returns 2" was not attainable under the city rule).
- **API (`go test ./...`, `go vet`):** table-driven per endpoint — happy path and every validation error, rate limit, CORS, compare ordering and deltas, search order, fail-closed on a corrupt fixture; the parity test in §7.
- **Web:** in the browser, walk landing → start → Maharashtra → Pune → toggle layers → switch preset → open Delhi from the compare panel; zero console errors; check 360 px and 1280 px; screenshots attached to the PR description.
- **Definition of done:** `cd ml && uv run pytest && uv run ruff check .` · `cd api && go vet ./... && go test ./...` · fixtures regenerated · ADR-0015 with the sensitivity table · README §9, §10, §12 and the AGENTS.md status and commands updated.

## 11. Risks and open items

- **City quality:** the urban-centre rule at 1 km can merge or split unexpected places; the review print in §5 and the spot checks catch the worst cases, and `name_overrides` fixes names.
- **OSM completeness** varies (new metro lines, station tagging); the score is labelled as based on community data, and GTFS metro stops are unioned where they exist.
- **GHSL at 1 km** and WorldPop 2020 are coarse; this is why the unit is ≈5 km², not smaller.
- **Growth favours the fringe, access favours the core** — the best cells tend to sit in the middle ring; stated in the methodology text, not hidden.
- **Delhi transit:** the GTFS feed is blocked (needs a manual download); Delhi uses OSM stations only until then.
- **Follow-ups, not v1:** past price index (license check first), pipeline projects from M3, Postgres store, login if a saved-list feature is ever wanted (needs an ADR).
