# Field: National Highways

- **Owner:** Punya · **Status:** active — starts at M1 · **Id:** `national_highways` · **Parameters:** `config/fields/national_highways.yaml`
- **Kinds:** `nh_segment`, `expressway_segment`, `toll_plaza`, `nh_project`, `la_notification`

## Scope

**In:** every National Highway in India (MoRTH, NHAI, NHIDCL, state PWD NH wings); access-controlled expressways whether built nationally or by a state — flagged with `owner_level`, because several major expressways are state-built; toll plazas; the NH project pipeline from announcement to opening, including land-acquisition notifications under the National Highways Act, 1956 (sections 3A and 3D); NH safety (accidents, black spots).

**Out for now:** other state highways and district roads (context only, from OSM), PMGSY rural roads and railways (future fields).

## Questions this field answers

For a pin — citizen or investor:

- Which NH or expressway serves this place: how far, how many lanes, is it tolled?
- What changed: when was the nearest corridor built or upgraded, and how did built-up area and night lights change along it?
- What's coming: NH projects nearby by stage and expected completion, and land-acquisition notifications in nearby villages — the earliest official signal of a new alignment.

For policy:

- Where do people live farthest from the NH network, relative to population?
- Which city pairs are badly connected — network distance far above straight-line distance — and does the pipeline fix them?
- Where are the safety hotspots: deaths per km, black spots, 2-lane undivided stretches?
- Where do residents ask for crossings, underpasses and service roads?
- Does NH investment go where the access gaps are?

## Sources

Each source goes through skill `add-data-source` before loading — license and terms first.

| Source | What it gives | Access | Used for |
|---|---|---|---|
| OpenStreetMap India — Geofabrik extract; Overpass for quick tests | NH and expressway geometry, `ref`, lanes, surface, maxspeed, bridges, toll booths, `construction` / `proposed` ways | Bulk PBF (ODbL) | Network, toll points, under-construction corridors |
| MoRTH Annual Report · Basic Road Statistics of India | Official NH length by state, lane-wise NH length, km built per year | PDF tables | Coverage reference, trends |
| data.gov.in — Parliament-answer tables | State-wise NH length over years, km built per year, black spots, NH accidents | CSV / API (GODL-India) | Trends, safety |
| MoRTH "Road Accidents in India" (annual) | Accidents and deaths on NHs by state | PDF tables | Safety rates |
| NHAI Toll Information System | Toll plazas: NH, location, rates | Portal | Toll layer, conflated with OSM toll booths |
| Bhoomi Rashi · eGazette | NH land-acquisition notifications — 3A (intent), 3D (declaration): NH number, villages | Portal search · gazette PDFs | Earliest pipeline signal |
| NHAI and MoRTH project pages · PIB (MoRTH) releases · CPPP and NHAI tenders · PARIVESH | Project stage, cost, dates | Web · RSS · portals | Pipeline events through the news AI |
| Shared layers | Population, GHSL, VIIRS, Open Buildings, LGD boundaries | — | Access, growth effect |

## Canonical mapping

| OSM | Kind | Status | Notes |
|---|---|---|---|
| Way with an NH ref (`ref` like `NH48`, or a member of an NH route relation), `highway` ∈ motorway, trunk, primary, secondary | `nh_segment` | operational | |
| `highway=motorway`, or an access-controlled `trunk` named "… Expressway" | `expressway_segment` | operational | `owner_level` = national or state |
| `highway=construction` + `construction` ∈ motorway, trunk, primary, with an NH ref or expressway name | same kinds | under_construction | Check against official openings — OSM lags |
| `highway=proposed` + the same | same kinds | proposed | |
| `barrier=toll_booth` within 50 m of an NH way | `toll_plaza` | operational | Conflate with the NHAI list |

Normalization rules — each one fails closed into `ingest_error`, never silently:

- **Refs:** OSM has `NH48`, `NH 48`, `NH-48`, `NH48;SH17` and pre-2010 numbers such as `NH4`. Split on `;`, normalize to `NH<number><suffix>`, and map old numbers through MoRTH's 2010 renumbering into `old_ref`.
- **Dual carriageways:** divided highways are drawn as two one-way ways, so naive length doubles. Measure along one direction of each route relation, or pair `oneway=yes` ways within ~30 m and count them once. The coverage report must agree with MoRTH totals within a documented gap.
- **Lanes:** OSM `lanes` is sparse. Record `lanes_source` (`osm`, `official`, `unknown`) and never impute silently; official lane-wise lengths exist only at state level.
- **Status:** OSM `construction` tags lag openings — confirm against official opening dates before calling a stretch under construction.

## EDA plan

Notebooks in `ml/notebooks/national_highways/`; logic in `ml/fields/national_highways/`.

| Notebook | Questions |
|---|---|
| `01_inventory` | NH km by state, OSM vs MoRTH; share of ways with a parseable ref; completeness of lanes, surface, maxspeed; network islands |
| `02_geometry_qa` | Dual-carriageway double counting; gaps in route relations; duplicate ways; stale construction tags |
| `03_growth_timeline` | Official NH km by year and state; lane mix over time; expressway opening timeline |
| `04_access` | Distance to the nearest NH for every H3 cell; population within 5, 10 and 25 km, by district; access vs population density |
| `05_corridor_effect` | Built-up and night-light growth within 0–2 km vs 2–10 km of expressways and upgrades opened 2005–2020, before vs after |
| `06_safety` | Deaths per 100 NH-km by state; black spots per 100 km; overlap with 2-lane undivided stretches |
| `07_pipeline` | Pipeline km by stage and state; land-acquisition notifications by district; access gain once the pipeline completes |

## Geospatial analysis

| Metric | Unit | Method |
|---|---|---|
| `nh_distance_km` | km, per H3 cell | KNN from the cell center to the nearest operational NH (v2: road-network distance) |
| `nh_access_band` | 0–5 / 5–10 / 10–25 / >25 km | From `nh_distance_km` |
| `pop_within_10km_share` | %, per district | Population within 10 km of an NH ÷ district population |
| `nh_density` | km per 1,000 km² and per lakh people, per district | Deduplicated NH length clipped to the district |
| `lane_mix` | % of NH km with ≤2, 4 and 6+ lanes, per state | OSM where tagged; official totals as the reference |
| `circuity` | ratio, per city pair | NH network distance ÷ straight-line distance for city pairs 100–600 km apart; high values flag missing links |
| `pipeline_access_gain_km` | km, per H3 cell | Today's `nh_distance_km` minus the same distance with approved and under-construction projects added — what the pipeline changes, not a forecast |
| `corridor_growth` | percentage points | Near-minus-far growth difference around dated openings (descriptive event study) |
| `death_rate` | deaths per 100 km per year, per state | Road Accidents in India ÷ NH length |

`circuity` needs a routable graph — use networkx (or pgRouting) and record the choice in README §11.

```yaml
# config/fields/national_highways.yaml — starting values; every number states its basis
h3_res: 8                                  # ADR-0004 default
access_bands_km: [5, 10, 25]               # team judgment, 2026-09
corridor_rings_km: { near: 2, far: [2, 10] }
city_pairs: { min_km: 100, max_km: 600, top_cities: 200 }   # team judgment, 2026-09
circuity_flag: 1.5                         # team judgment; tune after 04_access
toll_booth_snap_m: 50
dual_carriageway_pair_m: 30
```

## Layers and API

Common properties follow the shared contract in [`README.md`](README.md); field-specific extras:

| Layer | Geometry | Field-specific properties |
|---|---|---|
| `nh_segments` | LineString | `lanes`, `lanes_source`, `divided`, `surface`, `maxspeed`, `length_km`, `owner_level`, `old_ref` |
| `nh_projects` | LineString or Point | `stage`, `programme` (e.g. Bharatmala), `cost_crore`, `expected_completion`, `delay_months` |
| `toll_plazas` | Point | `fee_car` when available |
| `la_notifications` | Point — village centroid | `section` (3A or 3D), `notified_on`, `nh_ref` — village level only, never survey numbers or owner names (ADR-0011) |
| `nh_access` | H3 polygon | `nh_distance_km`, `nh_access_band`, `pipeline_access_gain_km` |

Area-profile section: nearest NH (ref, distance, lanes, tolled), NH projects within 25 km by stage, land-acquisition notifications within 10 km, corridor-growth evidence.

## Recommendations

1. **Crossings** — stretches that split populated areas, with crossing or underpass requests, accidents and 2-lane undivided carriageway → underpass or foot over-bridge.
2. **Capacity upgrades** — 2-lane stretches with high growth momentum, a high death rate and large populations served, not already in the pipeline → 4-laning candidate.
3. **Missing links** — city pairs above the circuity flag that the pipeline does not fix → link study.
4. **Access gaps** — dense districts more than 25 km from an NH and not covered by the pipeline.

Every recommendation carries drivers and evidence (README §8.3).

## Milestones and done checklist

- [ ] **M1 — data:** OSM NH network with normalized refs and single-counted length; toll plazas; MoRTH state totals; coverage report by state.
- [ ] **M1 — fixtures (first two days):** `web/fixtures/national_highways/nh_segments.geojson` and `toll_plazas.geojson`, simplified, ≤ 5 MB each.
- [ ] **M2 — analysis:** notebooks 01–04 and 06; `nh_access` metrics; first findings.
- [ ] **M2 — corridor effect:** notebook 05 with at least five dated openings.
- [ ] **M3 — pipeline:** projects and cited events (press releases, news, tenders, 3A/3D notifications); notebook 07; delay flags.
- [ ] **M4 — recommendations:** crossings and upgrades with drivers; the area-profile section is live.
- [ ] **Done bar:** every item in [`README.md`](README.md#the-done-bar--every-field-delivers-all-of-this); 5–10 findings below.

## Findings

_Add as analysis lands — statement, number, notebook, date._

## Open questions

- Is OSM lane tagging good enough anywhere, or do lane statistics stay state-level?
- Can land-acquisition notifications be fetched in bulk, or only searched? If only searched, which states first?
- Traffic volumes are not public — which proxies for capacity analysis (night lights, population, toll density)?
- State-built expressways: inside this field with `owner_level` (default), or a separate field?
