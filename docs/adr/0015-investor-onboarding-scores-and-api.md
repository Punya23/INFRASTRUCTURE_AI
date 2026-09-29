# ADR-0015: Investor onboarding — explainable city and area scores, served by a Go API before the database

- Status: Proposed
- Date: 2026-09-29
- Deciders: project team
- Related: README §2, §9, §10, §15 · ADR-0003, ADR-0004, ADR-0006, ADR-0007, ADR-0011, ADR-0012, ADR-0014 · [design spec](../superpowers/specs/2026-09-29-investor-onboarding-design.md)

## Context

Investors and homebuyers (README §2) ask "which state, city and area should I look at?" The product request was a flow: landing page, then a state, its top five cities with reasons, the best areas of a city on a map, and other cities compared in a side panel. The comparison was first phrased as yearly returns ("Pune 10%, Delhi 13%").

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
- Bad: the score says nothing about price, rent or timing, and users who came for returns will not find them; weights are judgment calls (mitigated by the published sensitivity summary below and drivers on every card); OSM completeness varies by city and is only labelled, not corrected; growth favours the fringe while access favours the core, so the best cells sit in the middle ring; fixtures for about 470 cities add tens of MB to the repo (gzip, budget 25 MB).

## Alternatives considered

- **Projected returns per city** — would need a superseding ADR for ADR-0003 and a price source that does not exist here; invites misuse as advice. A past-only official price index (RBI HPI) is a possible later addition after a license check.
- **Flask in `ml/`** — quicker, but ADR-0006 keeps Flask for the one AI call and makes Go the only public entry point.
- **Go with Postgres/PostGIS now** — the full M0 stack; much larger and nothing needs a database yet.
- **Email login** — needs personal-data storage, DPDP work and a database; nothing in v1 needs it.
- **GeoNames populations for city definition** — unreliable, see Context.

## Revisit when

M0 lands (swap the store for Postgres and move the pages into the Next.js app), when M3 brings cited pipeline events (add a pipeline factor), when an official price index is licensed, or when a saved-list feature justifies accounts.
