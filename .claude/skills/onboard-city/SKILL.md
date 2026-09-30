---
name: onboard-city
description: Use when adding a new city to INFRA-AI or replacing a showcase city. A city must be configuration plus a pipeline run — no code changes. Covers the city config, boundaries, languages, news queries, coverage checks and language evaluation.
---

# Onboard a city

The promise under test: **city #N = one config file + one pipeline run** (docs/PLAN.md §17, `AGENTS.md` invariant 8). Fields already cover all of India (ADR-0013); a city config adds local depth — boundaries, wards, languages, local news and sources. If adding a city needs a code change, the code is wrong — generalize the code; don't special-case the city.
Paths follow docs/PLAN.md §12; if one does not exist yet, create it there.

## 1. Write `config/cities/<city_id>.yaml`

Copy an existing city file and keep the keys identical (docs/PLAN.md Appendix A):

- `id` (lowercase slug), `name` in English and local script, state and ULB LGD codes (lgdirectory.gov.in)
- boundary and ward sources, each with an `as_of` date
- `languages` (BCP-47, most-spoken first — the first is the default reply language)
- news queries per language: every spelling and script of the city name × infrastructure keywords; known project and agency names
- local sources: metro / development authority / municipal press pages, state e-procurement, state RERA
- `h3_res` (default 8)

## 2. Boundaries

- Wards and city limits from DataMeet, OpenCity or the municipal GIS portal. National and state outlines only from the Survey of India–compliant layer (`AGENTS.md` invariant 6).
- Check: wards cover the city boundary with under 1 % gap or overlap.

## 3. Run the pipeline

- `make city CITY=<city_id>` (exists from M1): fetch → load → conflate → grid → scores → hotspots. It is idempotent — re-run until the coverage report is clean.

## 4. Coverage report — paste into the PR

- Per layer: count against a reference (for example, hospitals vs the data.gov.in / NHRR count), missing-attribute %, a map screenshot.
- Population total vs Census 2011 and WorldPop.
- News: articles discovered / kept / extracted over the last 12 months, by language.

## 5. Language readiness

A language new to the platform needs all of this before it is switched on anywhere:

- UI dictionary strings;
- at least 50 labeled citizen messages (including voice and romanized text) and 30 labeled articles in `ml/eval/`;
- a passing evaluation (skill `change-ai-pipeline`).

## 6. Document

- Showcase city? Update docs/PLAN.md §4 and write a superseding ADR for ADR-0002.
- Data gaps left? Add them to docs/PLAN.md §18.
