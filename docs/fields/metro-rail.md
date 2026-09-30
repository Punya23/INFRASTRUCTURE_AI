# Field: Metro rail

- **Owner:** _data teammate — add your name_ · **Status:** active — starts at M1 · **Id:** `metro_rail` · **Parameters:** `config/fields/metro_rail.yaml`
- **Kinds:** `metro_line`, `metro_station`, `rrts_line`, `rrts_station`, `monorail_line`, `metro_project`

## Scope

**In:** every metro system in India — operational, under construction, approved or proposed — plus RRTS (Namo Bharat) and monorail: lines, stations, phases, opening dates, ridership where public, station catchments and TOD influence zones.

**Out for now:** suburban and mainline rail (a future railways field), city buses (context for last-mile only), trams.

## Questions this field answers

For a pin:

- Which station is nearest — how far on foot, which line, is it open? If not, what stage is it at, when is it expected, and has that date slipped?
- What changed around stations after they opened (built-up area, night lights)?
- Is this place inside a TOD influence zone, existing or upcoming?

For policy:

- What share of each city's people live within 500 m and 1 km of a station — today, and once the pipeline is complete?
- Which dense, growing areas are more than 2 km from any existing or planned station?
- How does ridership compare with the projections the projects were approved on, and what might explain the gap — catchment, last-mile, integration?
- How well are stations connected to mainline rail, bus terminals and airports?
- What does a km cost, by city, and elevated vs underground?

## Sources

Each source goes through skill `add-data-source` before loading — license and terms first.

Verified on 2026-09-28 (links, access, license); re-check before loading.

| Source | What it gives | Access · license | Use |
|---|---|---|---|
| OpenStreetMap India | ~4.5k `railway=subway` ways, 121 `route=subway` relations, ~1.2k `station=subway` nodes, monorail; 390 `construction=subway` and 78 `proposed=subway` ways (taginfo, Sep 2026). RRTS is also tagged `subway` | Bulk download · ODbL | Lines, stations, pipeline geometry |
| [Wikidata](https://query.wikidata.org) | 971 Indian metro stations — 910 with coordinates, 840 with opening dates | SPARQL · **CC0** | Opening dates, station cross-check |
| [Wikipedia — Urban rail transit in India](https://en.wikipedia.org/wiki/Urban_rail_transit_in_India) | System and line tables: km, stations, opening dates | HTML · CC BY-SA (share-alike) | Cross-check only, cited |
| MoHUA figures via [Parliament answers](https://sansad.in/rs/questions/questions-and-answers) | ~1,159 km operational including 82 km RRTS (~1,077 km metro) in 26 cities; 886 km under construction (Monsoon session 2026) | HTML / PDF · public record | Reference totals — definitions differ, so store the source |
| Operator sites and reports (DMRC, BMRCL, CMRL, MMRCL, MMRDA, Maha Metro, GMRC, UPMRC, KMRL, HMRL, JMRC, …) · PIB Cabinet approvals | Official km, stations, phases, opening dates; sanctioned projects with cost and targets | Web (often JavaScript apps) · PDF · site terms | Reference totals, timelines, pipeline events |
| [NCRTC](https://ncrtc.in/details/) | Delhi–Meerut RRTS: 82 km, 16 stations plus 9 Meerut Metro stations, fully open since 22 Feb 2026 | HTML | RRTS layer |
| GTFS — [Hyderabad](https://hmrl.co.in/open-data/) (official) · [Delhi Metro via Delhi OTD](https://otd.delhi.gov.in/data/staticDMRC) (Aug 2023) · [Kochi](https://kochimetro.org/opendata/KMRLOpenData.zip) (calendar expired Dec 2025) · [Bengaluru](https://github.com/Vonter/bmrcl-gtfs) (community, approximate times) | Stops, routes, frequencies | ZIP · Hyderabad: free reuse with attribution; Delhi: registration form, proprietary terms; Kochi: attribution; Bengaluru: ODbL | Service levels where a feed is current. Chennai has only a stub and Mumbai none; more feeds in the [Mobility Database](https://files.mobilitydatabase.org/feeds_v2.csv) |
| Ridership — data.gov.in (Mumbai Lines 2A/7 and Monorail daily, Jan 2024–Sep 2025; Delhi Metro to 2021-22) · OpenCity (Bengaluru hourly by station, Aug–Sep 2025; Chennai monthly, Apr 2023–Jun 2026) · [L&T Metro Hyderabad](https://ltmetro.com/ridership/) (monthly) | City and station ridership | CSV · XLSX · HTML · GODL-India; the Bengaluru file is non-commercial | `04_ridership` |
| Projections — [CAG Report 11 of 2021](https://cag.gov.in/en/audit-report/details/114644) (Delhi Metro), Standing Committee on Housing and Urban Affairs, 13th Report 2021-22 (Bengaluru) | Actual vs projected or break-even ridership for specific cities | PDF | `ridership_ratio` — no multi-city dataset exists; build a curated table with a source per row |
| [National TOD Policy 2017](https://mohua.gov.in/static/uploads/2025/10/ba0cf0a6a17909cf36099ae402f2ab63.pdf) | Influence zone "generally up to a radius of nearly 500-800m" of a station; about 500 m either side of the corridor where stations are under 1 km apart (clause 7.1.2) | PDF | TOD zones |
| Shared layers | Population, GHSL, VIIRS, Open Buildings, Overture places (jobs proxy) | — | Catchments, growth effect |

## Canonical mapping

| OSM | Kind | Status | Notes |
|---|---|---|---|
| `railway=subway` or `light_rail` in a metro route relation | `metro_line` | operational | `line` from the relation name or colour; `elevation`: underground if `tunnel=yes`, elevated if `bridge=yes` or `layer>0`, else at grade |
| `railway=monorail` | `monorail_line` | operational | |
| RRTS (Namo Bharat) — tagged `railway=subway` in OSM | `rrts_line`, `rrts_station` | by tags | Separate from metro by `network` / `operator` (NCRTC) |
| `railway=construction` + `construction` ∈ subway, light_rail, monorail | `metro_line` | under_construction | Confirm against operator openings — OSM lags |
| `railway=proposed` + `proposed` ∈ subway, light_rail, monorail | `metro_line` | proposed | |
| `railway=station` + `station` ∈ subway, light_rail, monorail (or `public_transport=station` + `subway=yes`) | `metro_station` | operational | `interchange` when two or more lines share it |

Normalization rules — each one fails closed into `ingest_error`, never silently:

- **Double-tracked lines:** many lines are drawn one way per track, so naive length doubles. Measure along the route relation, or merge parallel tracks within ~20 m. Coverage must match operator km within a documented gap.
- **Station names:** English, Hindi and local-script names, "Metro Station" suffixes and renamed stations → a normalized key plus an alias table.
- **Several operators in one city** (Mumbai, Delhi NCR) → `agency` per line, never per city.
- **Opening dates:** OSM tags are sparse; fill them from Wikidata (CC0) and operator records, with the source on every date.
- **Reference totals disagree** by definition (metro only, with RRTS, Wikipedia's count): store every total with its source and as-of date.

## EDA plan

Notebooks in `ml/notebooks/metro_rail/`; logic in `ml/fields/metro_rail/`.

| Notebook | Questions |
|---|---|
| `01_inventory` | Cities, lines, stations; km operational, under construction and approved per city, OSM vs official; tag completeness (opening dates, elevation) |
| `02_timeline` | National metro km by year; phases per city; announced vs actual opening dates (delays) |
| `03_catchment` | Population within 500 m and 1 km of each station and city; today vs after the pipeline |
| `04_ridership` | Daily ridership vs projections by city; ridership per km and per station where published |
| `05_station_effect` | Built-up and night-light growth within 1 km of stations vs a 2–5 km ring, before vs after opening |
| `06_integration` | Distance from stations to mainline rail stations, bus terminals and airports; interchanges |
| `07_cost` | Cost per km by city and phase; underground share vs cost |

## Geospatial analysis

Catchments are walking-scale, so this field uses H3 resolution 9 (≈0.1 km² cells, ≈175 m edge) instead of 8.

| Metric | Unit | Method |
|---|---|---|
| `station_distance_m` | m, per H3 cell | KNN to the nearest operational station (v2: walking network) |
| `catchment_pop_500m`, `catchment_pop_1km` | people, per station | Population of cells within the radius |
| `city_coverage_share` | %, per city | People within 1 km of any station ÷ city population |
| `pipeline_coverage_gain` | percentage points, per city | Coverage with under-construction and approved stations added, minus today's |
| `transit_gap` | flag, per cell | Top population density and momentum, more than 2 km from any existing or planned station; Gi* groups these into corridors |
| `tod_zone` | polygon | 500 m and 800 m buffers around operational and upcoming stations; about 500 m either side of the corridor where stations are under 1 km apart (TOD Policy clause 7.1.2) |
| `integration_m` | m, per station | Distance to the nearest mainline rail station, bus terminal and airport |
| `ridership_ratio` | ratio, per city | Actual daily ridership ÷ projected |
| `station_effect` | percentage points | Near-minus-far growth difference around openings (descriptive event study) |

```yaml
# config/fields/metro_rail.yaml — starting values; every number states its basis
h3_res: 9                             # walking-scale catchments
catchment_radii_m: [500, 800, 1000]   # 500–800 m: National TOD Policy 2017 influence zone (clause 7.1.2); 1 km: common planning radius
transit_gap_km: 2                     # team judgment, 2026-09
parallel_track_merge_m: 20
effect_rings_km: { near: 1, far: [2, 5] }
```

## Layers and API

Common properties follow the shared contract in [`README.md`](README.md); field-specific extras:

| Layer | Geometry | Field-specific properties |
|---|---|---|
| `metro_lines` | LineString | `line`, `color`, `elevation`, `length_km`, `city`, `phase` |
| `metro_stations` | Point | `line`, `interchange`, `catchment_pop_1km`, `daily_ridership` when published |
| `metro_projects` | LineString or Point | `stage`, `phase`, `cost_crore`, `expected_completion`, `delay_months` |
| `tod_zones` | Polygon | `radius_m`, `station_id`, `status` |
| `metro_access` | H3 polygon (res 9) | `station_distance_m`, `transit_gap` |

Area-profile section: nearest station (line, distance, status, expected opening, delay history), TOD-zone membership, stations within 3 km by status, station-effect evidence.

## Recommendations

1. **Catchment-gap corridors** — dense, growing areas more than 2 km from any existing or planned station → corridor or extension study.
2. **Feeder and last-mile** — stations with large catchments but weak bus or feeder coverage, or ridership far below projection → feeder routes and footpaths.
3. **Integration** — stations within walking distance of a rail station or bus terminal but without a proper link → integration works.
4. **TOD planning** — upcoming stations with open or low-density land inside the influence zone → TOD planning (policy level, never parcels).

Every recommendation carries drivers and evidence (docs/PLAN.md §8.3).

## Milestones and done checklist

- [ ] **M1 — data:** OSM lines and stations per city with single-counted length; operator totals; coverage report per city.
- [ ] **M1 — fixtures (first two days):** `web/fixtures/metro_rail/metro_lines.geojson` and `metro_stations.geojson`, simplified, ≤ 5 MB each.
- [ ] **M2 — analysis:** notebooks 01–03 and 06; catchment and gap metrics; first findings.
- [ ] **M2 — effects and ridership:** notebooks 04, 05 and 07.
- [ ] **M3 — pipeline:** projects and cited events (Cabinet approvals, operator releases, news, tenders); delay flags.
- [ ] **M4 — recommendations:** catchment gaps and feeders with drivers; the area-profile section is live.
- [ ] **Done bar:** every item in [`README.md`](README.md#the-done-bar--every-field-delivers-all-of-this); 5–10 findings below.

## Findings

_Add as analysis lands — statement, number, notebook, date._

## Open questions

- GTFS is current only for Hyderabad (Delhi's is from 2023; Kochi's calendar has expired). Use timetable-free metrics (catchments, coverage) nationally, and GTFS service levels only where a feed is current?
- Station-level ridership is public only for Bengaluru (Aug–Sep 2025, non-commercial) — enough for a showcase-city analysis?
- RRTS and monorail: same field with their own kinds (default), or separate fields?
- Which projection counts when a DPR was revised?
