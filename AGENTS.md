# AGENTS.md — how to work in INFRA-AI

Read this before changing anything. It applies to people and AI coding agents alike. Claude Code loads it through `CLAUDE.md`; Codex, Cursor and other agents read it directly.

## What this repo is

A multilingual, location-first infrastructure intelligence platform for India, built as a Digital Public Good. Pin a place → what exists, what changed, what's coming (from news, press releases and tenders — cited), what residents are asking for, and where the gaps and priorities are. The full plan is [docs/PLAN.md](docs/PLAN.md).

## Status

Scope is field-first: **national highways** and **metro rail** across India (ADR-0013). National highways: M1 data and M2 analysis landed (`ml/fields/national_highways/`, findings in `docs/fields/national-highways.md`), and M3 is half done — delay flags and cited events from PIB press releases; news, tenders and land-acquisition notices are still open; metro starts M1. **Investor flow landed ahead of M0** (ADR-0015): `ml/pipeline/invest` exports city and area scores to `web/fixtures/invest/`, a stdlib Go API (`api/`) serves them, and static pages in `web/invest/` show landing, onboarding, state and city views. It has no database and no login; the store package is the seam where Postgres slots in. A static **BRICS page** (`web/brics.html`, upcoming, simulation on invented sample data for ten pilot cities; nothing ingested) previews the ten-member idea; scope stays India only until an ADR says otherwise. **Next: M0 — Foundation** (docs/PLAN.md §13: DB, API, UI shell). Update this line whenever a milestone lands.
ADR-0003 and ADR-0013 are Accepted; ADR-0001 is superseded; the others are Proposed pending team review — follow them as the working default.

## Read in this order

1. docs/PLAN.md §0–4 — product, users, problem-statement coverage, data scope (about 10 minutes).
2. [`docs/fields/`](docs/fields/README.md) — the field plans (national highways, metro rail), the done bar, and the shared layer contract the UI builds against.
3. Team research: [India_Existing_Project_Gaps.md](India_Existing_Project_Gaps.md) (why existing systems fall short) and [LokDristi_Datasets.md](LokDristi_Datasets.md) (dataset catalog, LGD join architecture). docs/PLAN.md §18 lists where they differ from the plan — those are open decisions, not settled ones.
4. [`docs/adr/`](docs/adr/README.md) — what was decided and why. To disagree, write a superseding ADR (skill `write-adr`); never silently diverge.
5. docs/PLAN.md §6–8 — architecture, data model, pipelines — before touching those areas.
6. The skill that matches your task (table below).

## Invariants — non-negotiable; every PR is reviewed against them

1. **Provenance on everything.** Every record carries `source`, `source_ref`, `fetched_at`, `license` and `confidence`. No anonymous data.
2. **Fail closed.** Invalid or ambiguous input goes to `ingest_error` or the review queue, or returns a 4xx. Never drop silently, never default silently. Unknown is not fine.
3. **AI never originates facts.** Extracted claims carry a verbatim evidence quote that code verifies against the source. Briefs cite fact ids and use only numbers present in those facts; on validation failure they fall back to templated output. (ADR-0008)
4. **Explainable analytics only.** Scores are config-weighted sums of observable facts with stored `drivers`. No predictive or black-box models. (ADR-0003)
5. **Privacy by default.** No raw phone numbers, names or contact details outside the opt-in `contact` table. Redact before storage and before any hosted model; public outputs are aggregates with counts below 5 suppressed. Never collect Aadhaar. (ADR-0011)
6. **Official boundaries.** National and state outlines come only from the Survey of India–compliant layer. (ADR-0007)
7. **Licenses before data.** Check terms before ingesting; OSM attribution and ODbL share-alike on OSM-derived exports; news stored as metadata + a short quote + link. (ADR-0012)
8. **City- and field-agnostic core.** No city names, bounding boxes, languages or thresholds in code — only in `config/cities/*.yaml`, `config/fields/*.yaml` and `config/scoring.yaml`. Field logic lives in `ml/fields/<field>/`; shared code never special-cases a field. (ADR-0013)
9. **Idempotent pipelines.** Upsert on `(source, source_ref)` or the provider message id; every step can re-run safely.
10. **Contract-first API.** `api/openapi.yaml` is the source of truth; web types are generated from it; SQL goes through sqlc. (ADR-0006)
11. **Swappable AI providers.** Each AI capability is one function in `ml/ai/`; the provider is picked by an environment variable; no provider SDK calls anywhere else. (ADR-0008)
12. **Lean stack.** No new service, datastore or dependency without an ADR. Postgres does geometry, search, vectors and the queue. (ADR-0005)

## Conventions

- **Go (`api/`)** — `cmd/` + `internal/` layout; stdlib `net/http` routing; pgx + sqlc, no ORM; `context` with a timeout on all I/O; wrap errors with `%w`; validate at the handler boundary; table-driven tests.
- **Python (`ml/`)** — 3.12, type hints, ruff for lint and format, pytest. Pipeline steps are plain functions behind a thin CLI; the Flask app stays thin (parse → call → return); notebooks import from `ml/` and hold no logic of their own.
- **TypeScript (`web/`)** — Next.js App Router; server components by default, `"use client"` only for the map and interactive parts; Tailwind; strict mode; API types generated from OpenAPI; UI strings in per-language dictionaries (en, hi, kn), never hard-coded.
- **Site header** — one component, `web/site-header.js` (+ `site-header.css`), mounted by every page; add or rename a nav link there, never in a page. `web/links.test.mjs` fails if a page grows its own header.
- **SQL (`db/migrations/`)** — plain numbered SQL, forward-only; geometry in EPSG:4326 with GiST indexes; constraints (CHECK, UNIQUE, FK) in the database, not only in application code.
- **Config** — YAML; every number carries a comment with its basis (a norm, a source, or "team judgment, <date>").
- **Commits and PRs** — small, one concern each; the message says what changed and why; the PR template checklist is filled in.

## Definition of done

- A test or runnable check fails if the new logic breaks, and the whole suite passes.
- Every invariant the change touches still holds.
- Docs are updated in the same PR: the README section, an ADR if a decision changed, a skill if a workflow changed.
- AI changes attach the gold-set evaluation table; scoring changes attach the sensitivity summary.

## Skills — `.claude/skills/`

| Skill | Use when |
|---|---|
| [`add-data-source`](.claude/skills/add-data-source/SKILL.md) | Adding or changing any dataset, scrape, feed or raster |
| [`onboard-city`](.claude/skills/onboard-city/SKILL.md) | Adding a city or replacing a showcase city |
| [`change-ai-pipeline`](.claude/skills/change-ai-pipeline/SKILL.md) | Touching prompts, schemas, models, speech, translation, embeddings or briefs |
| [`change-scoring`](.claude/skills/change-scoring/SKILL.md) | Touching indices, weights, norms, hotspots or recommendations |
| [`add-api-endpoint`](.claude/skills/add-api-endpoint/SKILL.md) | Adding or changing a Go or Flask endpoint or a webhook |
| [`write-adr`](.claude/skills/write-adr/SKILL.md) | Making or challenging a significant decision |
| [`add-field`](.claude/skills/add-field/SKILL.md) | Starting or restructuring a field — one type of infrastructure covered for all of India |

Claude Code discovers these automatically. Other agents and people: open the matching `SKILL.md` — it is plain Markdown.

## Commands

Python lives in `ml/` (uv project, Python 3.12):

```bash
cd ml && uv sync                                        # environment
cd ml && uv run python -m common.fetch                  # download every source in config/sources.yaml
cd ml && uv run python -m fields.national_highways all  # NH field: extract → … → analyze → fixtures
cd ml && uv run python -m fields.public_transport.gtfs all  # GTFS feeds: validate → NH/toll link → fixtures
cd ml && uv run pytest && uv run ruff check .           # checks before every commit
cd ml && uv run python -m fields.public_transport.upcoming build  # upcoming bus/metro projects from news → web/fixtures/invest/projects.json (fetch needs APIFY_TOKEN; ADR-0016)
cd ml && uv run python -m pipeline.invest all           # investor flow: cities → facts → export to web/fixtures/invest (also osm, sensitivity)
```

Go API and investor pages (repo root):

```bash
go -C api run ./cmd/api                                  # serve /v1/* on :8080 from web/fixtures/invest (see api/README.md)
go -C api vet ./... && go -C api test ./... -race        # API checks before every commit
python3 mock_api.py                                      # no Go? same /v1/* from the fixtures on :8080 (PORT=8081 for a second checkout)
python3 -m http.server 8765 --directory web              # pages at http://localhost:8765/invest/ (CORS default matches this port)
node --test 'web/invest/js/*.test.mjs'                   # page logic tests
node --test web/links.test.mjs                         # every page link resolves (no bare #, missing file or anchor)
node --test web/brics-sim.test.mjs                     # BRICS page simulation checks (quote, redaction, score, brief)
cd ml && uv run python ../scripts/build_brics_map.py   # rebuild web/brics-world.json (Natural Earth 110m, generalised)
scripts/deploy-vercel.sh [--prod]                        # stage web/ + /v1 function (mock_api.py) → Vercel deploy → smoke test; --stage-only / --smoke URL
# .github/workflows/deploy-vercel.yml runs it with --prod on every push to main that touches web/, mock_api.py or deploy/ (repo secrets VERCEL_TOKEN, VERCEL_ORG_ID, VERCEL_PROJECT_ID)
```

Still to come at M0: `docker compose up`, `make migrate`, `make city CITY=<id>`, `make eval CAP=<capability>`. Document each one here the moment it exists.

## When unsure

- Product or scope question → add it to docs/PLAN.md §18 and ask the team; don't guess.
- Technical choice with trade-offs → skill `write-adr`, status Proposed.
- Data looks wrong → don't "fix" it silently in code; route it to `ingest_error` and note it in the EDA report.
