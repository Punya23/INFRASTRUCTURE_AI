---
name: add-api-endpoint
description: Use when adding or changing an INFRA-AI HTTP endpoint — a Go API route, a Flask ML endpoint or a messaging webhook. Contract-first (OpenAPI → sqlc → handler → generated web client) with boundary validation, timeouts, privacy rules and tests.
---

# Add or change an endpoint

Read first: docs/PLAN.md §10 (API) · ADR-0006 (services) · `AGENTS.md` invariants 2, 5, 10.
Paths follow docs/PLAN.md §12; if one does not exist yet, create it there.

## Order: contract first

1. **Spec** — `api/openapi.yaml`: path, parameters, request and response schemas, with examples. The examples double as frontend fixtures.
2. **SQL** — `api/internal/store/queries/*.sql`, then `sqlc generate`. Spatial filters use index-friendly operators (`ST_DWithin`, `&&`, KNN `<->`), never `ST_Distance(...) < x` over a whole table.
3. **Handler** — `api/internal/http/`:
   - validate at the boundary: latitude and longitude in range and inside India's bounding box, radius ≤ 10 km, enums, `limit` ≤ 100;
   - `context.WithTimeout` on every database and ML call;
   - errors as `{"error": {"code": "...", "message": "..."}}` — never internal details.
4. **Client** — regenerate the web client in `web/lib/api/` from the spec; never hand-write response types.
5. **Tests** — a handler test for the happy path and each validation error; an integration test for new SQL against the Compose Postgres.

## Webhooks

- Verify the signature before anything else (WhatsApp `X-Hub-Signature-256` HMAC; Telegram secret-token header).
- Insert the raw message into `inbound_message` (unique provider message id) and return 200 immediately. Processing happens in the worker; never call ML from a webhook.

## Flask (`ml/app.py`)

- Stay thin: parse → call one function in `ml/ai` → return. Request-size limits, timeouts, schema validation.

## Public data rules

- Citizen data leaves the API only as aggregates (issue counts — never message text or reporter data); counts below 5 at hexagon level are suppressed.
- Exports are non-PII and include license and attribution.
