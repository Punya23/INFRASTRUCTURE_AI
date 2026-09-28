---
name: add-data-source
description: Use when adding or changing any dataset or feed in INFRA-AI — an OSM/Overture layer, a government portal, a tender/RERA/clearance scrape, a news feed, a population or satellite raster. Enforces the license check, provenance fields, taxonomy mapping, idempotent loading, fail-closed validation and doc updates.
---

# Add or change a data source

Read first: `AGENTS.md` invariants 1, 2, 7, 8, 9 · README §5 (source table) and §8.1 (ingestion) · ADR-0012 (licensing) · your field plan in `docs/fields/`.
Paths follow README §12; if one does not exist yet, create it there.

## 1. Is it worth it?

- Which of the five questions does it answer (what's here / what changed / what's coming / what people need / so what)? Which index or view uses it?
- Is it already covered? Improving conflation of an existing source beats adding a loader.
- Needs a new service, datastore or paid dependency? Stop and write an ADR first (skill `write-adr`).

## 2. License and terms — before downloading anything

- Record the license, the attribution text and the terms URL. Acceptable: ODbL, CC BY / BY-SA, CDLA, GODL-India, public domain, public records.
- Scraping: obey robots.txt and the site terms, throttle to at most 1 request per second unless the source allows more, and send a descriptive User-Agent.
- Behind a login, registration form or CAPTCHA? A person downloads it by hand and the manifest says how. Never automate past a CAPTCHA or login.
- Services that advertise write operations (for example WFS-T): send read-only requests only.
- News and other text: keep metadata, a short evidence quote and the link — never republish full text.
- License unclear? Do not ingest. Add it to README §18.

## 3. Fetch

- Write to `data/raw/<source>/<YYYY-MM-DD>/` (gitignored) and commit `data/manifests/<source>.yaml` with: url, fetched_at, sha256, license, attribution, row count.
- Fetching is re-runnable; raw files are never edited.
- Check the content type and file signature, not just HTTP 200 — dead government links often return an HTML page with status 200.

## 4. Load — `ml/fields/<field>/ingest_<source>.py` (field sources) or `ml/pipeline/ingest_<source>.py` (shared sources)

- Map source fields and tags to canonical kinds through `config/taxonomy.yaml`; never inline mappings in code.
- Every row carries `source`, `source_ref` (a stable upstream id), `fetched_at`, `license` and `confidence`.
- Upsert into `raw_<source>` on `(source, source_ref)` — loading twice must not duplicate anything.
- City names, boundaries and languages come from `config/cities/*.yaml`, never from code.
- Drop personal fields at ingest — names, phone numbers, survey or plot numbers (ADR-0011).
- Geometry: EPSG:4326, made valid, inside India's bounding box. Anything that fails goes to `ingest_error` with a reason. Never drop rows silently.

## 5. Conflate

- Same kind + within the distance threshold + similar name (trigram) → merge into one `asset` and append to its `sources`.
- Thresholds live in config; log merge counts on every run.

## 6. Leave a check behind

- One pytest in `ml/tests/` with a tiny fixture of real upstream records covering: tag mapping; idempotency (load twice → same count); bad geometry → `ingest_error`.
- Run EDA notebook `01_inventory` for the affected cities: counts, coverage map, missing-attribute %, overlap with existing sources. Put the key numbers in the PR.

## 7. Document in the same PR

- A row in README §5: layer, linked source, license, what it is used for.
- Attribution on the app's About page if the license requires it.
- If it changes what an index means, also follow skill `change-scoring`.
