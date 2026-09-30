# Field: National Highways

- **Owner:** Punya · **Status:** active — M1 data and M2 analysis done; M3 partly done (delay flags and cited events from PIB press releases; news, tenders and land-acquisition notices open) · **Id:** `national_highways` · **Parameters:** `config/fields/national_highways.yaml`
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

Verified on 2026-09-28 (links, access, license); re-check before loading.

| Source | What it gives | Access · license | Use |
|---|---|---|---|
| [OpenStreetMap India](https://download.geofabrik.de/asia/india.html) — Geofabrik: 1.6 GB PBF, updated daily; six zone extracts also as GeoPackage and shapefile | NH ways (`highway=trunk` + `ref=NH44`), `ref:old` on ~63% and `lanes` on ~58% of trunk ways, expressways, construction and proposed ways, ~2.7k toll-booth nodes (taginfo, Sep 2026) | Bulk download · ODbL | Primary network layer |
| [data.gov.in](https://data.gov.in) — Rajya Sabha answer tables | State-wise 2-, 4- and 6–8-lane NH length with the balance under construction and awarded (2024-25); NH built 2019-20 to 2023-24; Bharatmala awarded and built; NH-wise black-spot counts (2016–18, 2017–19); NCRB road-class accidents 2023 | Small CSVs · GODL-India | Lane check, trends, safety |
| MoRTH Annual Report 2024-25 · Basic Road Statistics 2020-22 ([morth.gov.in](https://morth.gov.in)) | NH length 1,46,195 km, state-wise NH list, Bharatmala components; NH series 1950–2022 (as of 31 Mar 2022); lane figures only nationally | PDF — the 2025-26 report is scanned and needs OCR · none stated | Reference totals, long-run trend |
| [PIB Year End Review 2025](https://pib.gov.in/PressReleasePage.aspx?PRID=2209837) · [Parliament questions](https://sansad.in/rs/questions/questions-and-answers) | NH 1,46,560 km, 3,052 km access-controlled, 43,512 km with 4+ lanes; the freshest figures, and the source of most data.gov.in tables | HTML / PDF · public record | Latest totals — keep the as-of date |
| MoRTH Road Accidents in India 2023 and 2024 ([2024 CSVs on OpenCity](https://data.opencity.in/dataset/road-accidents-in-india-2024)) | State-wise NH accidents, deaths and injuries, 2021–24 | PDF; the CSVs lack the NH annexures · none stated | Safety rates |
| [IHMCL NH fee plazas](https://ihmcl.co.in/wp-content/uploads/2025/08/NH-Fee-Plazas-1.pdf) (Aug 2025) | ~1,159 plazas: state, district, section, NH — no coordinates | PDF · none stated | Toll list, matched to OSM toll booths |
| [Wikipedia — Expressways of India](https://en.wikipedia.org/wiki/Expressways_of_India) | Named expressways with reported opening dates (operational and partially-opened only) | HTML · CC BY-SA 4.0 | Corridor-effect opening dates where OSM has none (secondary source — lower confidence) |
| [NHAI Datalake — Projects under Execution](https://datalakeg.nhai.gov.in/nhai/mISC/DataLakeGISDashboard) | Project code, NH, lanes, cost, progress %, dates | Web map · none stated | Pipeline stages |
| [Bhoomi Rashi](https://bhoomirashi.gov.in) | Project search with 3a/3A/3D dates and land-acquisition cost; Highway Land Register with Excel export | Web forms behind a CAPTCHA — manual exports only · none stated | Land-acquisition timeline |
| [eGazette](https://egazette.gov.in) | Section 3A/3D notifications: NH, chainage, village, survey numbers, area, owner names | Individual PDFs, search UI · government publication | Earliest pipeline signal — keep NH, chainage, village and date; drop survey numbers and owner names at ingest |
| [MoRTH press releases](https://morth.nic.in/press-release) → their pages on [PIB](https://pib.gov.in) — the listing is JSON at `morth.nic.in/backend/api/press-release`, about 150 releases since March 2026 | Cabinet approvals, contract awards, bid responses, DPR starts, milestones — each with a verbatim sentence | HTML · Government of India; [PIB Copyright Policy](https://pib.gov.in/content/102_2_Copyright-Policy.aspx): free reproduction, source acknowledged, third-party material excluded | Cited events (`nh_events.json`). No robots.txt on either site; PIB's firewall answers 403 to bot-style user agents, so the fetch sends a plain descriptive one at 1 request per second |
| NHAI project dashboard layer — `NHAI:adv_upc_wise_alignments_wfs_layers` on the same GeoServer | 1,812 projects with LOA, appointed and scheduled-completion dates, capital cost and physical progress (`dd-mm-yyyy` text); PD/RO phone numbers, drone-video names and office fields are not kept | WFS, no login · **no license stated** ([ADR-0014](../adr/0014-nhai-geoserver-data.md)) | Delay flags — aggregates only |
| PIB (other) · CPPP and NHAI tenders · PARIVESH | Announcements, tenders, clearances | Web · RSS · portals — NHAI's own press-release and tender APIs sit behind a CAPTCHA | News and tenders are not built yet |
| NHAI GeoServer — `datalakew.nhai.gov.in/geoserver/NHAI/ows` | 7,452 NH segments (lanes, greenfield flag, completion FY23–26), 1,010 project alignments, 678 toll plazas, 91,508 crash points 2020–23 with a black-spot flag, Bharatmala corridors — roughly a 2023 snapshot | WFS GeoJSON, no login · **no license stated** | Used for analysis under [ADR-0014](../adr/0014-nhai-geoserver-data.md): read-only requests, keep-lists at fetch, only aggregates committed — never NHAI geometry or records |
| Community extracts — [india-geodata](https://github.com/yashveeeeeeer/india-geodata) (GatiShakti-MoRTH NH lines, Jun 2022), [ramSeraph/indian_transport](https://github.com/ramSeraph/indian_transport) | NH lines and tolls scraped from official portals | GitHub releases · upstream unlicensed, whatever the label says | Cross-check only; never redistribute |
| Shared layers | Population, GHSL, VIIRS, Open Buildings, LGD boundaries | — | Access, growth effect |

Not usable now: the NHAI Toll Information System (unreachable; the last community scrape is from 2022) · PM GatiShakti (government login; "GatiShakti Public" needs registration and is view-only) · Bhuvan (WMS images only) · DataMeet (no NH layer) · NHAI's website project lists (`nhai.gov.in/assets/json/get_*_projects.json` — DPR in progress, to be awarded, under implementation, O&M, current-year targets): they carry `likely_completiondate` and more, but are a 2021 snapshot — the newest award and appointment dates are September 2021 and their stage labels agree with the live layer for only 7% of shared projects · NHAI's `press-release` and `tenderlist` APIs (CAPTCHA field in every request; a person would have to export them).

## Canonical mapping

| OSM | Kind | Status | Notes |
|---|---|---|---|
| Way with an NH ref (`ref` like `NH48`, or a member of an NH route relation), `highway` ∈ motorway, trunk, primary, secondary | `nh_segment` | operational | |
| `highway=motorway` (National Expressways), or `highway=trunk` with `expressway=yes` or `motorroad=yes` | `expressway_segment` | operational | `owner_level` = national or state |
| `highway=construction` + `construction` ∈ motorway, trunk, primary, with an NH ref or expressway name | same kinds | under_construction | Check against official openings — OSM lags |
| `highway=proposed` + the same | same kinds | proposed | |
| `barrier=toll_booth` within 50 m of an NH way | `toll_plaza` | operational | Conflate with the NHAI list |

Normalization rules — each one fails closed into `ingest_error`, never silently:

- **Refs:** ways mostly carry `NH44`, with variants `NH 44`, `NH-44` and lists like `NH44;NH48`; the per-state route relations (`network=IN:NH`) carry a bare `ref=48` plus `is_in:state`, and superroutes carry `ref=NH48`. Split on `;`, normalize everything to `NH<number><suffix>`, and take `old_ref` from OSM's `ref:old` (on ~63% of trunk ways), cross-checked with MoRTH's 2010 renumbering.
- **Dual carriageways:** divided highways are drawn as two one-way ways (about 72% of NH trunk ways are one-way), so naive length doubles. Measure along one direction of each route relation, or pair `oneway=yes` ways within ~30 m and count them once. The coverage report must agree with MoRTH totals within a documented gap.
- **Lanes:** OSM `lanes` covers about 58% of trunk ways (48.7% of operational NH length) and counts one carriageway, so a paired one-way way carries half the road's lanes (`road_lanes`). Record `lanes_source` (`osm`, `official`, `unknown`), never impute silently, and check totals against the official state-wise 2/4/6–8-lane lengths on data.gov.in.
- **Status:** OSM `construction` tags lag openings — confirm against official opening dates before calling a stretch under construction.
- **Reference totals disagree** by definition and date (1,46,195 km in the 2024-25 Annual Report vs 1,46,560 km in PIB's Year End Review 2025): store every total with its source and as-of date, and name the one each coverage report compares against.
- **Personal data:** gazette schedules list owner names and survey numbers, and NHAI's toll layer lists staff names and phone numbers — drop those fields at ingest (ADR-0011).

## EDA plan

Notebooks in `ml/notebooks/national_highways/`; logic in `ml/fields/national_highways/`.

| Notebook | Questions |
|---|---|
| `01_inventory` | NH km by state, OSM vs MoRTH; share of ways with a parseable ref; completeness of lanes, surface, maxspeed; network islands |
| `02_geometry_qa` | Dual-carriageway double counting; gaps in route relations; duplicate ways; stale construction tags |
| `03_growth_timeline` | Official NH km by year and state; lane mix over time; expressway opening timeline |
| `04_access` | Distance to the nearest NH for every populated 1 km pixel, rolled up to H3 and state (district once LGD boundaries land); population within 5, 10 and 25 km; density; city-pair circuity |
| `05_corridor_effect` | Built-up growth (GHSL 2000→2020) within 0–2 km vs 2–10 km of expressways opened 2001–2019, against corridors not yet open; night lights next |
| `06_safety` | National and state NH totals from Road Accidents in India 2024's Annexures 9–10 (OCR'd, gridlines stripped, verified against the printed Table 2.5 total) over official state NH km; crash density by lane band from NHAI's 2022–23 crash points; black-spot status |
| `07_pipeline` | Pipeline km by state and target year; NHAI project stages; access gain once the pipeline completes; schedule and delay flags by state (aggregates, ADR-0014); cited stage events from MoRTH press releases; land-acquisition notices stay open |
| `08_tolls_traffic` | Tolled length and fees by class and state (class mapping checked against Fee Rules 2008); traffic-count coverage and count points per 100 km |

Reproduce: `cd ml && uv run python -m common.fetch && uv run python -m fields.national_highways all` (about 10 minutes on a laptop; the first run also downloads about 150 PIB release pages at one per second, later runs fetch only new releases), then run the notebooks. HTML exports are in `ml/notebooks/national_highways/reports/`.

## Geospatial analysis

| Metric | Unit | Method |
|---|---|---|
| `nh_distance_km` | km, per H3 cell | KNN from the cell center to the nearest operational NH (v2: road-network distance) |
| `nh_access_band` | 0–5 / 5–10 / 10–25 / >25 km | From `nh_distance_km` |
| `pop_within_10km_share` | %, per state (district at M3) | Population within 10 km of an NH ÷ district population |
| `nh_density` | km per 1,000 km² and per lakh people, per state | Official state length ÷ equal-area state area and WorldPop population |
| `lane_mix` | % of NH km with ≤2, 4 and 6+ lanes, per state | OSM where tagged; official totals as the reference |
| `circuity` | ratio, per city pair | NH network distance ÷ straight-line distance for city pairs 100–600 km apart; high values flag missing links |
| `pipeline_access_gain_km` | km, per H3 cell | Today's `nh_distance_km` minus the same distance with approved and under-construction projects added — what the pipeline changes, not a forecast |
| `corridor_growth` | percentage points | Near-minus-far growth difference around dated openings (descriptive event study) |
| `death_rate` | deaths per 100 km per year, per state | RAI 2024 state NH deaths (OCR'd Annexures 9–10) ÷ official state NH km |
| `delay_flag` | overdue · scheduled_ahead · not_started · unknown, per NHAI project; counts and shares per state | Under construction with a passed scheduled-completion date = overdue (driver: `days_overdue`); awarded but never appointed = not_started (driver: days since LOA). Projects with a provisional completion certificate are not assessed. No progress-versus-plan score — see below |

`delay_flag` reads the NHAI dashboard layer at the fetch date. The layer has no date for a provisional completion certificate, so a passed scheduled date says nothing about a project that already carries one. A straight-line "physical progress vs elapsed time" score was tried and dropped: progress follows an S-curve, so even a strict cutoff labelled 83% of not-yet-overdue projects "behind". The scheduled date is the one on NHAI's dashboard and may already include time extensions — `overdue` is slippage against the current recorded schedule, not the original contract date. Per-project rows stay in `data/`; only state and national aggregates are committed (ADR-0014).

`circuity` routes on a networkx graph of operational roads (trunk to tertiary, not NH-only — NHs alone break where they cross cities on untagged roads) and links (docs/PLAN.md §11); dead ends within `graph_snap_m` of another node are joined, because OSM ways often meet without sharing a node.

Every threshold lives in [`config/fields/national_highways.yaml`](../../config/fields/national_highways.yaml), each with its basis.

## Layers and API

Common properties follow the shared contract in [`README.md`](README.md); field-specific extras:

| Layer | Geometry | Field-specific properties |
|---|---|---|
| `nh_segments` | LineString | `lanes`, `lanes_source`, `divided`, `surface`, `maxspeed`, `length_km`, `owner_level`, `old_ref` — the fixture carries `lanes_band`, `owner_level`, `length_km` |
| `nh_projects` | LineString or Point | `stage`, `programme` (e.g. Bharatmala), `cost_crore`, `expected_completion`, `delay_months` — not committed as records (ADR-0014); `nh_delays.json` carries the state aggregates |
| `nh_project_events` | none (keyed by `nh_refs` and `states`) | `event_type`, `event_date`, `nh_refs`, `states`, `cost_crore`, `length_km`, `modes`, `evidence` (one verbatim sentence), `source_url`, `extractor`, `language` — fixture `nh_events.json`; geocoding to a place comes with the shared news AI |
| `toll_plazas` | Point | `fee_car` when available |
| `la_notifications` | Point — village centroid | `section` (3A or 3D), `notified_on`, `nh_ref` — village level only, never survey numbers or owner names (ADR-0011) |
| `nh_access` | H3 polygon | `nh_distance_km`, `nh_access_band`, `pipeline_access_gain_km` — the fixture (H3 res 4, to stay under 5 MB) adds `population`, `share_within_10km` |

Area-profile section: nearest NH (ref, distance, lanes, tolled), NH projects within 25 km by stage, land-acquisition notifications within 10 km, corridor-growth evidence.

## Recommendations

1. **Crossings** — stretches that split populated areas, with crossing or underpass requests, accidents and 2-lane undivided carriageway → underpass or foot over-bridge.
2. **Capacity upgrades** — 2-lane stretches with high growth momentum, a high death rate and large populations served, not already in the pipeline → 4-laning candidate.
3. **Missing links** — city pairs above the circuity flag that the pipeline does not fix → link study.
4. **Access gaps** — dense districts more than 25 km from an NH and not covered by the pipeline.

Every recommendation carries drivers and evidence (docs/PLAN.md §8.3).

## Milestones and done checklist

- [x] **M1 — data:** OSM NH network with normalized refs and single-counted length; official state totals with as-of dates; coverage report by state; OSM toll booths matched to the IHMCL list (90.1% national coverage).
- [x] **M1 — fixtures (first two days):** `web/fixtures/national_highways/nh_segments.geojson` and `toll_plazas.geojson`, simplified, ≤ 5 MB each.
- [x] **M2 — analysis:** notebooks 01–04 and 06; `nh_access` metrics; first findings; city-pair routing on the full road graph (trunk to tertiary).
- [x] **M2 — corridor effect:** notebook 05 with 12 dated openings (2001–2019) from Wikipedia's "Expressways of India".
- [x] **M3 — projects, schedules and delay flags:** NHAI's dashboard layer (`adv_upc_wise_alignments_wfs_layers`) carries appointed and scheduled-completion dates — the older `upc_wise_alignments_wfs_layer` has none, which is why delay flags first looked blocked. State aggregates in `nh_delays.json`, notebook `07_pipeline`.
- [x] **M3 — cited events from official press releases:** 22 stage events from MoRTH's releases on PIB, each with a verbatim, code-verified sentence and a link (`nh_events.json`); every listed release is accounted for in `press_releases.csv`. Rules, not an LLM: these are formulaic English releases from one official source, so title rules plus a code-checked verbatim sentence meet ADR-0008's guardrails without a provider key. When news or Hindi arrive, an LLM extractor in `ml/ai/` replaces the title rules and reuses the same check (`pipeline/evidence.py`) and review queue.
- [ ] **M3 — news and tenders:** not started. News needs the shared news AI (ADR-0008: discovery, de-duplication, an LLM with a gold set — no provider key or labelled articles exist yet); NHAI's tender and press-release APIs and CPPP's tender search all ask for a CAPTCHA, so a person would have to export them.
- [ ] **M3 — 3A/3D land-acquisition notices:** blocked. eGazette has no bulk access and Bhoomi Rashi is CAPTCHA-gated; MoRTH's own gazette listing holds NH declarations and entrustments, not 3A/3D notices. Needs a person to export a first batch.
- [ ] **M4 — recommendations:** crossings and upgrades with drivers; the area-profile section is live.
- [ ] **Done bar:** every item in [`README.md`](README.md#the-done-bar--every-field-delivers-all-of-this); 5–10 findings below.

## Findings

As of 2026-09-29, from the OSM extract of 2026-09-28. Notebooks are in `ml/notebooks/national_highways/`.

1. **OSM covers 97.8% of official NH length.** 1,42,905 km of single-counted NH in OSM, against 1,46,194 km in MoRTH Appendix-2 (as on 31.12.2024). NHAI's own layer holds 1,36,758 km (93.5%). Arunachal Pradesh is the outlier at 57% in both sources. UP, Haryana, Rajasthan and MP are 7–10% over, likely from untagged state roads under the bare-`trunk` convention. — `01_inventory`
2. **Divided highways double naive length.** Raw operational way length is 1,99,362 km; after pairing opposite one-way carriageways it is 1,46,322 km. 2,768 km get their NH ref only from route relations, and 5,823 km of `trunk` carry no ref. The trunk-with-other-ref rule (SH, Bangladesh `N` roads) is what brings OSM near the official total. — `02_geometry_qa`
3. **Most NH is still two lanes or fewer.** In NHAI's layer, 99,931 of 1,36,758 km (73%) are ≤2 lanes; 4-lane is 31,729 km and 6+ is 5,097 km. OSM tags lanes on only 48.6% of NH length, so NHAI is the lane source for analysis. — `01_inventory`
4. **79.0% of Indians live within 10 km of an operational NH or expressway**; 58.9% within 5 km. 3.68 crore people are more than 25 km away. Among large states, Chhattisgarh (63.2%), Rajasthan (64.2%) and Madhya Pradesh (64.7%) have the lowest 10-km share. — `04_access` (WorldPop 2020, straight-line distance)
5. **The pipeline moves 10-km access from 79.0% to 80.6%, about 2.14 crore people.** The largest gains are in Uttar Pradesh (46 lakh), Karnataka (25 lakh) and West Bengal (20 lakh); Rajasthan and MP barely change (+0.3 pp). The pipeline counts OSM construction/proposed ways and NHAI stretches with an FY23–26 target (11,392 km, almost all greenfield). — `04_access`, `07_pipeline`
6. **NHAI's crash layer is a partial record.** It has 49,992 crash points for 2023, against 1,08,240 accidents on NHAI roads in Road Accidents in India 2024 (Table 2.10). Its deaths (6,274 in 2023) are about 13% of the 49,675 RAI reports for NHAI roads. So the layer shows where crashes cluster, not death rates. Crash points per km rise with width (6+ lanes: 128 per 100 km per year; 2 lanes: 9.5), but that mixes traffic volume with the layer's better coverage of NHAI-run corridors. — `06_safety`
7. **NH road deaths rose every year, 2020–2024:** from 50,251 to 64,772. That is 36.6% of all road deaths on about 2% of road length. 77% of NH deaths in 2024 were on NHAI-managed NHs. — `06_safety` (RAI 2024, Tables 2.5 and 2.10)
8. **City-pair circuity drops once routing uses the full road graph.** Median 1.18 over 1,543 pairs (was 1.31 on the NH-only graph, which broke where NHs cross cities on untagged roads). — `04_access`
9. **Corridor effect, now with dated openings:** 12 expressways opened 2001–2019 (999 eff-km — Outer Ring Road, Agra–Lucknow, Yamuna, Mumbai–Pune among the largest), matched by name to Wikipedia's "Expressways of India" since OSM tags `opening_date`/`start_date` on only 5,218 of 32,302 expressway segments. Near-minus-far built-up growth (0–2 km vs 2–10 km, GHSL 2000→2020) is −0.02 pp for these corridors and −0.06 pp for ones not yet open: a difference of 0.04 pp, i.e. no measurable concentration of growth right along new expressways at 1 km resolution (descriptive, not causal; growth rose about equally across the whole 0–10 km band — 1.9 pp vs 1.0 pp around unopened corridors). — `05_corridor_effect`
10. **Toll coverage: OSM has 90.1% of the IHMCL plaza count nationally**, with 151 of 1,044 OSM plazas matched to an IHMCL code by name; Bihar (56%) and Odisha (69%) lag. The 26 IHMCL plazas without a NETC code get a stable `S<serial>` id, so they can still be matched, and duplicate codes raise. — toll_coverage_by_state
11. **State NH death rates, now from RAI's own annexures, not NHAI's partial crash layer.** Delhi (164/100 km) and Puducherry (164/100 km) are the highest; the state annexures were OCR'd (gridlines stripped) and verified against RAI's printed Table 2.5 total. — `06_safety`

12. **A quarter of NHAI's completed NH is tolled:** 33,594 of 1,37,517 km (24.4%). The median single-journey fee is ₹75 for a car and ₹260 for a bus or truck. Rajasthan is the most tolled large state (54% of its length). NHAI's fee columns follow the Fee Rules 2008 class ratios (LCV 1.62, bus/truck 3.38, 3-axle 3.75, 4–6 axle 5.29, 7+ axle 6.42 × car), and the build fails if they drift more than 10%. — `08_tolls_traffic`
13. **NHAI counts traffic on 53% of its NH length, but the counts can't be used yet.** Its 14 traffic columns carry no legend anywhere NHAI publishes, and no column is a total. They are profiled, not interpreted. The labelled `traffic_survey` layer has 4,179 confirmed count points, 2.9 per 100 official km (Karnataka 4.0; Andhra Pradesh 1.9). So per-vehicle crash rates remain blocked. — `08_tolls_traffic`
14. **Two in three of NHAI's projects under construction are past their scheduled completion.** As of 2026-09-29, 264 of 388 are overdue (68% of the 387 with a usable schedule): a median 572 days (about 19 months) late, and already 82% built. They carry ₹3.29 lakh crore of the ₹4.87 lakh crore under construction. Kerala (16 of 16), Jammu and Kashmir (13 of 14), Rajasthan (10 of 11) and Maharashtra (24 of 27) are worst; Jharkhand (4 of 18) and Telangana (4 of 12) best. The date is the one on NHAI's dashboard and may already include time extensions, so this is slippage against the current recorded schedule. — `07_pipeline`
15. **28 awarded NHAI projects never started:** a median 237 days since the letter of award with no appointed date. West Bengal (8) and Uttar Pradesh (6) hold half of them. — `07_pipeline`
16. **Official press releases give 22 dated, cited stage events in seven months:** 9 Cabinet approvals worth ₹52,764 crore, one revised Cabinet cost (₹3,631 crore), one ministerial approval (₹1,428 crore), 5 contract awards, 4 bid responses, one DPR start and one tunnel breakthrough (Zojila), across 13 states and UTs. Of 154 listed MoRTH entries, 125 are not project events (tolling, safety, policy, ministerial reviews, explainers), 3 are Hindi and not extracted, and 4 have no release text; none is dropped silently. — `07_pipeline`

## Open questions

- NHAI GeoServer — decided in ADR-0014: used for analysis, aggregates only. Still open: send the terms request to NHAI and record the reply.
- Land acquisition: Bhoomi Rashi is CAPTCHA-gated (manual exports) and eGazette has no bulk access — which corridors to export by hand first, and is extracting gazette PDFs worth it for M3?
- NH declarations and entrustments: MoRTH's gazette listing (`morth.nic.in/backend/api/gazettes-notifications`) holds 222 "NH Declaration" and 61 "NH Entrustment" PDFs with dates — the formal step that makes a road an NH. Worth parsing for "when did this become an NH", or out of scope?
- News and tenders: needs the shared news AI (ADR-0008) — an LLM provider key, a gold set (150 labelled articles in en/hi/kn) and a home for the events. Until then only official releases feed events; Hindi releases are listed but not extracted.
- Event geometry: press-release events carry `nh_refs` and `states`, not a place. Match them to OSM `proposed`/`construction` ways by NH ref and name, or wait for the shared gazetteer geocoder?
- Lanes: OSM tags lanes on 48.7% of NH length; NHAI's layer covers every completed stretch. Use NHAI bands for analysis and OSM only for display — or wait for the data.gov.in state lane table?
- Traffic volumes: NHAI's `nh_network_of_india_new` has 14 unlabelled traffic count columns on 53% of NH length. Ask NHAI for the column legend (with the ADR-0014 terms request); until then no per-vehicle rates.
- State-built expressways: inside this field with `owner_level` (default), or a separate field?