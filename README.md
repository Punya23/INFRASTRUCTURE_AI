# INFRA-AI

**Pin any place in India. See what exists, what is being built, and what is coming, with every claim cited.**

A multilingual, location-first infrastructure intelligence platform for India, built as a Digital Public Good. It joins roads, metro, rail, press releases and population data by place, so one pin answers: what is here, what changed, what is coming, and where the gaps are. Scope today: **national highways** and **metro rail** (ADR-0013). Scores are explainable sums of observable facts. No predictive model; AI only reads text, and quotes are verified against the source.

## What is built

Everything runs from files in this repo. There is no database, login or hosted AI yet (next: M0 foundation).

| Piece | What it does | Where |
|---|---|---|
| Explore | Search a city; map with bus and metro routes (5 cities), scores, projects in the news; 18 UI languages, voice input | `web/index.html` |
| NH Explorer | 1,42,905 km of national highways, 1,044 toll plazas, 10 km population access, transit layers | `web/nh-explorer.html` |
| Policymaker View | State-wise highway length, OSM coverage, deaths per 100 km, tolls, traffic; CSV export | `web/policymaker.html` |
| Invest flow | 381 cities, 36 states and UTs, four score presets, area hexagons, compare, onboarding; every score shows its drivers | `web/invest/`, `ml/pipeline/invest` |
| Go API | 9 read endpoints under `/v1`; contract in `api/openapi.yaml`; `mock_api.py` serves the same without Go | `api/`, `mock_api.py` |
| BRICS page | Upcoming. Runs the pipeline on invented sample data for a pilot city in each of ten members. Nothing is fetched | `web/brics.html` |
| NH field data | OSM, MoRTH, NHAI, WorldPop joined; 16 findings; delay flags; cited PIB events | `ml/fields/national_highways/`, `docs/fields/national-highways.md` |
| Public transport | 8 GTFS feeds (38,797 stops) for Bengaluru, Chennai, Hyderabad, Mumbai, Pune; 44 upcoming projects from news | `ml/fields/public_transport/` |
| Geography | LGD states, districts, sub-districts, ULBs, wards | `ml/fields/geography/` |
| Pitch deck | 8 slides: problem, solution, screenshots, feasibility, BRICS | `docs/INFRA-AI-pitch.pptx` |

**Not built yet:** Postgres, citizen intake (voice, WhatsApp), AI briefs on live data, the metro field, tenders and land-acquisition notices, hotspots and recommendations.

## Run it

```bash
python3 mock_api.py                          # /v1/* on :8080 (or: go -C api run ./cmd/api)
python3 -m http.server 8765 --directory web  # open http://localhost:8765/
```

Checks before a commit:

```bash
cd ml && uv run pytest && uv run ruff check .
go -C api vet ./... && go -C api test ./... -race
node --test 'web/invest/js/*.test.mjs' web/links.test.mjs web/brics-sim.test.mjs
```

More commands (data pipelines, deploy) are in [AGENTS.md](AGENTS.md).

## Read next

- [docs/PLAN.md](docs/PLAN.md): the full plan (problem, users, data, architecture, milestones)
- [AGENTS.md](AGENTS.md): how to work here, and the twelve invariants every change is reviewed against
- [docs/adr/](docs/adr/README.md): what was decided and why
- [docs/fields/](docs/fields/README.md): one plan per field
