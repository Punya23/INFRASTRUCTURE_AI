---
name: add-field
description: Use when starting a new INFRA-AI field — one type of infrastructure covered for all of India and owned end to end (for example railways, airports, water canals, health facilities) — or when restructuring an existing field. Covers the field plan, taxonomy kinds, parameters, sources, UI fixtures, EDA, geospatial analysis, layers, pipeline and the done bar.
---

# Add a field

Read first: ADR-0013 (field-first scope) · [`docs/fields/README.md`](../../../docs/fields/README.md) (done bar, shared layer contract, template) · an existing plan as the example ([`national-highways.md`](../../../docs/fields/national-highways.md)) · `AGENTS.md` invariants 1, 2, 7, 8.
Paths follow README §12; if one does not exist yet, create it there.

## 1. Scope it — one page, before any data

- Copy the template from `docs/fields/README.md` to `docs/fields/<field>.md` and add an index row with owner and status.
- Write the scope (in and out) and the questions the field must answer, for a pin and for policy. If a question needs another field's data, record the dependency — don't pull that data in.

## 2. Kinds and parameters

- Add the field's kinds and tag → kind/status mappings to `config/taxonomy.yaml`.
- Create `config/fields/<field_id>.yaml` for field parameters (distances, bands, H3 resolution), each with a comment giving its basis.
- Field logic lives in `ml/fields/<field_id>/`. Shared code never special-cases a field.

## 3. Sources

- Every source goes through skill `add-data-source`: license first, manifest, idempotent loader, fail-closed validation, a test.
- Include at least one official reference total (km, counts) to measure coverage against.

## 4. Fixtures for the UI — early

- In the first days, commit simplified samples that follow the shared layer contract to `web/fixtures/<field_id>/<layer>.geojson` (≤ 5 MB each). Tell the UI owners the layer names and any field-specific properties.

## 5. EDA

- Notebooks in `ml/notebooks/<field_id>/NN_name.ipynb`; logic is imported from `ml/fields/<field_id>/`; each exports HTML to `ml/notebooks/<field_id>/reports/`.
- Start with an inventory notebook (coverage vs the official reference, attribute completeness) and a geometry-QA notebook (double counting, stale statuses, duplicates).

## 6. Geospatial analysis

- Metrics per H3 cell and per district or city, each with drivers (ADR-0003), parameters read from `config/fields/<field_id>.yaml`.
- At minimum: access or coverage now; the change once the pipeline completes; the past growth effect where opening dates exist.
- A new analysis library gets a line in README §11; a new service or datastore needs an ADR (skill `write-adr`).

## 7. Pipeline and news

- Field projects and events flow through the shared news AI; add the field's keywords to the news queries. Prompt or schema changes follow skill `change-ai-pipeline`.

## 8. Layers, API and recommendations

- Map layers follow the shared contract plus the field-specific properties documented in the plan; add the field's section to the area profile (skill `add-api-endpoint`).
- At least one recommendation type with drivers and evidence (skill `change-scoring` for scores).

## 9. Done

- Tick every item of the done bar in `docs/fields/README.md`; write the 5–10 findings in the plan (statement, number, notebook, date); update the index status and the field table in README §4.
