# Architecture Decision Records

Short records of significant decisions — context, decision, consequences, alternatives. They explain *why* the code looks the way it does. How to write one: skill [`write-adr`](../../.claude/skills/write-adr/SKILL.md).

## Index

| # | Decision | Status |
|---|---|---|
| [0001](0001-t-shaped-data-scope.md) | T-shaped data scope: every layer for two pilot cities, backbone networks for all of India | Superseded by ADR-0013 |
| [0002](0002-pilot-cities.md) | Pilot cities: Bengaluru and Lucknow — now the demo's showcase cities (ADR-0013) | Proposed |
| [0003](0003-explainable-analytics-no-prediction.md) | Explainable indices and spatial statistics — no predictive model | Accepted |
| [0004](0004-h3-grid-spatial-key.md) | H3 resolution-8 grid as the spatial join key; LGD codes for administrative joins | Proposed |
| [0005](0005-postgres-single-datastore.md) | PostgreSQL + PostGIS as the only datastore, including the job queue | Proposed |
| [0006](0006-three-service-monorepo.md) | One monorepo, three deployables: Next.js web, Go API, Python ML and pipeline | Proposed |
| [0007](0007-open-map-stack.md) | Open map stack: MapLibre, open basemap, vector tiles from PostGIS, Survey of India boundaries | Proposed |
| [0008](0008-llm-boundary.md) | LLMs read, structure and summarize — evidence-verified, cited and provider-swappable | Proposed |
| [0009](0009-language-stack.md) | Indian-language stack: Bhashini and AI4Bharat, English canonical text, originals kept | Proposed |
| [0010](0010-citizen-intake.md) | Citizen intake: WhatsApp first, Telegram and web fallbacks, persist-then-acknowledge processing | Proposed |
| [0011](0011-privacy-do-no-harm.md) | Privacy and do-no-harm by design (DPDP-aligned) | Proposed |
| [0012](0012-licensing-open-standards.md) | Licensing and open standards | Proposed |
| [0013](0013-field-first-scope.md) | Field-first scope: national highways and metro rail first, then one field at a time | Accepted |
| [0014](0014-nhai-geoserver-data.md) | Use NHAI Datalake GeoServer data for analysis; publish aggregates only | Accepted |

**Statuses:** Proposed → Accepted → Deprecated, or Superseded by ADR-NNNN. Proposed ADRs are the working default until the team reviews them. An accepted decision is never rewritten — a new ADR supersedes it.

## Template

```markdown
# ADR-NNNN: <the decision, in one short sentence>

- Status: Proposed
- Date: YYYY-MM-DD
- Deciders: <names, or "project team">
- Related: <README sections, ADRs, issues>

## Context
<Forces, constraints and facts — why a decision is needed now.>

## Decision
<What we will do, in active voice, specific enough to check in code review.>

## Consequences
- Good: …
- Bad: …

## Alternatives considered
- <Option> — <why not>

## Revisit when
<An observable trigger, e.g. "intake sustains more than 200 messages per second".>
```
