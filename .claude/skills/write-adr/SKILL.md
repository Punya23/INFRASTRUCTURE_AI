---
name: write-adr
description: Use when making or changing a significant INFRA-AI decision — a new service, datastore or dependency; data scope or pilot-city changes; what a score means; AI provider or model tier; privacy, licensing or standards; anything hard to reverse or likely to be questioned. Also use when you disagree with an existing ADR.
---

# Write an ADR

## When

Write one if the decision is hard to reverse, touches more than one component, adds a dependency or service, or a reasonable teammate would ask "why did we do it this way?". Routine choices inside an accepted decision don't need one.

## How

1. Number = the highest number in `docs/adr/` + 1, zero-padded to four digits.
2. Copy the template from `docs/adr/README.md` to `docs/adr/NNNN-short-kebab-title.md`.
3. Fill in:
   - **Context** — facts and forces, including constraints from `AGENTS.md`;
   - **Decision** — active voice, specific enough to check in code review;
   - **Consequences** — good and bad;
   - **Alternatives considered** — at least one real alternative, and why not;
   - **Revisit when** — an observable trigger.
4. Status starts as `Proposed` and becomes `Accepted` after team review. Never rewrite the decision of an accepted ADR: write a new one and mark the old one `Superseded by ADR-NNNN`.
5. Add a row to the index in `docs/adr/README.md`, and link the ADR from the README section it affects.
6. Keep it under about 60 lines; link evidence (evaluation tables, benchmarks) rather than pasting it.
