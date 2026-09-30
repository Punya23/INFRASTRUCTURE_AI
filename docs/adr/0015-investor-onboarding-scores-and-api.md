# ADR-0015: Investor onboarding — explainable city and area scores, served by a Go API before the database

- Status: Proposed
- Date: 2026-09-29
- Deciders: project team
- Related: docs/PLAN.md §2, §9, §10, §15 · ADR-0003, ADR-0004, ADR-0006, ADR-0007, ADR-0011, ADR-0012, ADR-0014 · [design spec](../superpowers/specs/2026-09-29-investor-onboarding-design.md)

## Context

Investors and homebuyers (docs/PLAN.md §2) ask "which state, city and area should I look at?" The product request was a flow: landing page, then a state, its top five cities with reasons, the best areas of a city on a map, and other cities compared in a side panel. The comparison was first phrased as yearly returns ("Pune 10%, Delhi 13%").

Three facts constrain it. ADR-0003 (Accepted) rules out prediction, the plan lists price forecasting under "Won't", and no dataset in the repo can support a return figure. M0 (Postgres, Go API, Next.js shell) has not started, yet the UI needs a real backend now. And GeoNames populations are unreliable as a city definition (Kallakurichi shows 1.68 M; Delhi is split into Rohini and Narela).

## Decision

- **Score, not returns.** Rank cities and areas by an explainable Access + Momentum score: five observed factors (NH access, rail access, metro access, road-network strength, built-up growth 2000 → 2020), piecewise-linear sub-scores, four preset weightings (balanced, commuter, highway, growth) in `config/scoring.yaml`, and stored drivers. A factor that was not observed is dropped and the weights renormalised — never scored as zero. No return, price or forecast number appears anywhere; a test guards the copy.
- **Cities and areas.** A city is an urban centre (UN Degree of Urbanisation: contiguous WorldPop 2020 cells at ≥ 1,500 people/km²) cut at state borders, with ≥ 100,000 people. Areas are H3 resolution-7 cells (≈ 5.2 km², matching the 1 km rasters) — a per-layer resolution, which ADR-0004 allows. GeoNames supplies names and centres only; a reviewed `name_overrides` list fixes names such as Gurugram.
- **Bus is shown, not scored.** GTFS exists for five cities; a factor present for some cities would break comparability across cities.
- **Serving.** The pipeline (`ml/pipeline/invest`) exports JSON fixtures to `web/fixtures/invest/`. A stdlib-only Go API (`api/`, contract `api/openapi.yaml`) loads them at start-up, fails closed on a malformed file, and serves `/v1/states`, `/v1/states/{code}/cities`, `/v1/cities`, `/v1/cities/{id}`, `.../areas`, `.../assets` and `.../compare`. Static pages in `web/invest/` consume it. The Go store holds no scoring logic; a parity test ties served scores to the exported sub-scores and weights.
- **No database and no login in v1.** Nothing writes data; the store package is the seam where Postgres slots in at M0. The visitor's state and preset stay in `localStorage`; no personal data is collected (invariant 5).
- **Compare panel.** Other cities are ranked by the same preset score with per-factor sub-score differences as the "why" (`delta`, `better`, `worse`); default scope is other metros for a metro, similar-size cities otherwise.

## Consequences

- Good: every number answers "why?"; the flow ships without waiting for M0; the API contract is fixed for the future Postgres store and the Next.js shell; the same pipeline output feeds both.
- Bad: the score says nothing about price, rent or timing, and users who came for returns will not find them; weights are judgment calls (mitigated by the published sensitivity summary below and drivers on every card); OSM completeness varies by city and is only labelled, not corrected; growth favours the fringe while access favours the core, so the best cells sit in the middle ring; the 381 cities of the first run add 9.2 MB of gzip fixtures to the repo (budget 25 MB); 40 urban-centre pieces of 100,000+ people that GeoNames cannot name are held back for review (Goa, Sikkim, Arunachal, Ladakh and the Lakshadweep have no city as a result), and in dense plains the 1,500 people-per-cell rule chains villages into very large "cities" (Muzaffarpur about 11 M), which the page shows as given.

## Known limits of the first run

Found in review of the real data; none is hidden by the UI and none is a reason to hold the release, but each needs an owner.

- **Merged urban centres.** Contiguous 1,500 people/km² cells chain villages together on dense plains. Seven cities exceed 8 M people; outside the real metros Muzaffarpur (11.0 M, 9,281 km², more cells than Kolkata) is the clear case, with Kozhikode (5.8 M) and Gurugram (4.3 M, spanning Faridabad and Sonipat) behind it. Mumbai (23.1 M) and Kolkata (22.8 M) are also larger than their urban agglomerations. Population and area on a page describe the whole contiguous dense zone. A later ADR should add a built-up-share criterion from the GHSL layer already loaded, or cap extent from the anchor; no per-city hack.
- **Unnamed pieces are held back, not guessed.** 40 pieces of 100,000+ people (9.6 M people) have no GeoNames place inside them and are dropped to a review list; the largest are in West Bengal and Bihar, one in Karnataka (about 506,000, near Dharwad) and Kohima in Nagaland. State pages therefore read "Only N cities above 1 lakh people" even where a qualifying but nameless piece exists. `name_overrides` is keyed by a GeoNames id inside the piece and cannot fix them; a piece-anchor override or nearest-place naming within a configured distance is the follow-up.
- **Goa has no city** because its largest contiguous zone holds about 82,000 people, not because pieces were dropped. The spec's "Goa returns 2 cities" was not attainable under the city rule and has been corrected.
- **46 % of areas have no name** (no OSM place within 2.5 km) and 12 % of city-preset best areas are unnamed; the pages say "an unnamed area in {city}" or show coordinates. An API field for the nearest named place would allow "Area near …".
- **Hyderabad bus data is non-commercial.** The TGSRTC feed's terms permit non-commercial and research use only. Its stop counts appear in Hyderabad's assets and cards, with the licence recorded in `bus_source`, the city record and `meta.sources`. Under ADR-0012 this is a release blocker for any commercial deployment until the licence is checked with the publisher.
- **Growth knots re-anchored.** The spec's first knots left about 94 % of areas below the watch-out line; the shipped knots follow the measured distribution (p50 0.9, p90 3.9, p99 12.1 pp).

## Sensitivity summary

Scoring changes must attach one (AGENTS.md, definition of done). The weights are judgment calls, so we measure how much they matter. For each state with at least five cities, every preset weight is moved by a random ±30 % and renormalised (200 draws per preset, seed 20260929); the table gives the mean share of the state's top five that stays in its top five. Source: `python -m pipeline.invest sensitivity` (`data/processed/invest/sensitivity.md`, git-ignored, regenerated with the fixtures).

| preset | mean top-5 overlap (19 states, 366 cities) | lowest state |
|---|---:|---|
| balanced | 0.95 | HR 0.85, KL 0.86 |
| commuter | 0.96 | TN 0.86, GJ 0.87, KL 0.87 |
| highway | 0.97 | MP 0.83, GJ 0.91 |
| growth | 0.97 | MH 0.90, PB 0.90 |

Spearman rank correlation of city scores between presets is 0.89 (commuter vs highway) to 0.97 (balanced vs commuter). Reading: the shortlist is stable under weight noise (at least four of five cities survive on average), but presets are not interchangeable: commuter and highway disagree most, which is the point of offering them. A state whose overlap is below 0.9 has a close race for fifth place, and the drivers shown on each card, not the rank order, are what a reader should trust there.

## Alternatives considered

- **Projected returns per city** — would need a superseding ADR for ADR-0003 and a price source that does not exist here; invites misuse as advice. A past-only official price index (RBI HPI) is a possible later addition after a license check.
- **Flask in `ml/`** — quicker, but ADR-0006 keeps Flask for the one AI call and makes Go the only public entry point.
- **Go with Postgres/PostGIS now** — the full M0 stack; much larger and nothing needs a database yet.
- **Email login** — needs personal-data storage, DPDP work and a database; nothing in v1 needs it.
- **GeoNames populations for city definition** — unreliable, see Context.

## Revisit when

M0 lands (swap the store for Postgres and move the pages into the Next.js app), when M3 brings cited pipeline events (add a pipeline factor), when an official price index is licensed, or when a saved-list feature justifies accounts.
