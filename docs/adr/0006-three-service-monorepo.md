# ADR-0006: One monorepo, three deployables — Next.js web, Go API, Python ML and pipeline

- Status: Proposed
- Date: 2026-09-28
- Deciders: project team
- Related: docs/PLAN.md §6, §10, §12 · ADR-0005, ADR-0008 · skill `add-api-endpoint`

## Context

Team standards: Next.js and TypeScript for the frontend, Go or NestJS for the backend, Python with Flask for machine learning. Python owns the geo-data and ML ecosystems; the public API needs to be small, fast and typed. A DPG needs a clean public API others can build on. Four people must work in parallel from day one.

## Decision

- One repository; three deployables:
  - `web/` — Next.js App Router;
  - `api/` — Go: public REST API with OpenAPI 3.1, vector tiles, messaging webhooks, dashboard auth. **The only public entry point.**
  - `ml/` — Python: Flask for the one synchronous AI call (area briefs), a queue worker, the batch pipeline as CLI commands (cron in production), and notebooks.
- `api/openapi.yaml` is the contract; web types are generated from it; SQL goes through sqlc.
- Go → Flask calls have timeouts; when Flask fails, the API returns the facts without the narrative.

## Consequences

- Good: each part uses the strongest ecosystem; ownership is clear; the contract lets everyone start at once.
- Bad: two backend languages; one cross-service call path to keep healthy.

## Alternatives considered

- Next.js route handlers as the only backend — mixes the public API with the UI; a poor fit for webhooks, tiles and long jobs.
- NestJS instead of Go — viable; Go chosen for tile performance and small binaries.
- FastAPI for everything — one fewer language; the fallback if the team has no Go capacity.
- One microservice per capability — operations overhead with no benefit at this size.

## Revisit when

The Go layer becomes thin enough to fold elsewhere, or the team lacks Go capacity (then FastAPI, via a superseding ADR).
