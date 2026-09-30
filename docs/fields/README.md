# Fields

A **field** is one type of infrastructure — national highways, metro rail, … — covered for all of India and owned end to end by one person. Fields are added one at a time ([ADR-0013](../adr/0013-field-first-scope.md)); the workflow for a new one is skill [`add-field`](../../.claude/skills/add-field/SKILL.md).

## Index

| Field | Id | Status | Owner | Plan |
|---|---|---|---|---|
| National Highways | `national_highways` | Active — data, EDA and analysis done; pipeline half done (delay flags, cited press-release events); news, tenders, land-acquisition notices and recommendations next | Punya | [national-highways.md](national-highways.md) |
| Metro rail | `metro_rail` | Active — starts at M1 | _data teammate — add your name_ | [metro-rail.md](metro-rail.md) |
| Railways | `railways` | Candidate | — | — |
| Airports | `airports` | Candidate | — | — |
| Water — canals and irrigation | `water` | Candidate | — | — |
| Health facilities, schools | `health`, `education` | Candidate | — | — |

## The done bar — every field delivers all of this

1. **Sources** — each one passed skill `add-data-source`: license checked, manifest committed, idempotent loader, fail-closed validation, a test.
2. **Canonical data** — rows in `asset`, `project` and `project_event` with the field's kinds from `config/taxonomy.yaml`, plus a coverage report against an official reference total (km, station counts, …) with the gap explained.
3. **EDA** — notebooks in `ml/notebooks/<field>/` answering the questions in the field plan; HTML reports committed.
4. **Geospatial analysis** — field metrics per H3 cell and per district or city, each with its drivers: access or coverage now, the change once the pipeline completes, and the past growth effect where opening dates exist.
5. **Findings** — 5–10 evidence-backed statements in the field plan, each with a number, the notebook that produced it and a date.
6. **Layers and API** — map layers following the contract below, fixtures for the UI, and the field's section in the pin area profile.
7. **Pipeline** — the field's projects with stage timelines and cited events (news AI, press releases, tenders, notifications).
8. **Recommendations** — at least one recommendation type with drivers and evidence.

## Shared layer contract — what the UI builds against

Every feature in every field layer (GeoJSON now, vector tiles later) carries these properties. Geometry is EPSG:4326.

| Property | Type | Meaning |
|---|---|---|
| `id` | string | Stable id: `<kind>:<source>:<source_ref>` |
| `field` | string | `national_highways`, `metro_rail`, … |
| `kind` | string | From `config/taxonomy.yaml` — e.g. `nh_segment`, `toll_plaza`, `metro_line`, `metro_station` |
| `name` | string or null | Display name |
| `ref` | string or null | Route or line id — `NH48`, `Purple Line` |
| `status` | enum | `proposed`, `approved`, `tendered`, `under_construction`, `operational`, `stalled`, `cancelled` |
| `opened_on` | string or null | ISO 8601 date, or a year |
| `expected_completion` | string or null | ISO 8601 `YYYY-MM` |
| `agency` | string or null | Owning agency — NHAI, BMRCL, … |
| `source` | string | Primary source id |
| `confidence` | number | 0–1 |

Field-specific properties are listed in each field plan. The UI must render any field from these common properties alone, and treat field-specific ones as extras.

**Area profile section** — each field adds one entry to `GET /v1/area` (docs/PLAN.md §10). Illustrative, not real data:

```json
{
  "field": "national_highways",
  "summary": { "nearest_ref": "NH48", "nearest_km": 3.4, "lanes": 4 },
  "assets": [{ "id": "nh_segment:osm:way/123", "kind": "nh_segment", "status": "operational", "distance_km": 3.4 }],
  "projects": [{ "id": "nh_project:news:42", "name": "Example bypass", "stage": "tendered", "expected_completion": "2028-03", "sources": 3 }]
}
```

**Fixtures** — field owners commit simplified samples that follow this contract to `web/fixtures/<field>/<layer>.geojson` (≤ 5 MB each) in the first days of M1, so the UI never waits for the API. Full datasets stay out of git.

Fixtures under `web/fixtures/` are not all one field's. `web/fixtures/invest/` is cross-field: the investor flow (ADR-0015) scores cities and areas from the national highways, metro and rail, and public transport layers together, so no single field owns it. It is written by `ml/pipeline/invest`, served by the Go API in `api/`, and each file carries its own provenance. A field change that alters a layer the scores read (for example NH segments or transit stops) means regenerating it with `cd ml && uv run python -m pipeline.invest all`.

## Template for a new field plan

Copy into `docs/fields/<field>.md` (kebab-case file name) and add a row to the index.

```markdown
# Field: <name>

- Owner: <name> · Status: <candidate / active / done> · Id: `<field_id>` · Parameters: `config/fields/<field_id>.yaml`

## Scope
## Questions this field answers
## Sources
## Canonical mapping
## EDA plan
## Geospatial analysis
## Layers and API
## Recommendations
## Milestones and done checklist
## Findings
## Open questions
```
