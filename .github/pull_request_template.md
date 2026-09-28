## What and why

<!-- One paragraph. Link the README section, milestone or issue this serves. -->

## How it was verified

<!-- Tests run, evaluation table, coverage numbers, screenshots. -->

## Checklist — see AGENTS.md "Definition of done"

- [ ] A test or runnable check covers the new logic; the full suite passes locally
- [ ] New records carry provenance (`source`, `source_ref`, `fetched_at`, `license`, `confidence`); licenses checked and README §5 updated
- [ ] Invalid or unknown input fails closed (`ingest_error`, review queue or 4xx) — nothing dropped or defaulted silently
- [ ] No PII in analytics tables, logs or public endpoints; public counts below 5 suppressed
- [ ] AI changes: evidence verified, outputs cited, prompt version recorded, gold-set evaluation table attached
- [ ] Scoring changes: sensitivity summary attached; `drivers` still explain every score
- [ ] No city-specific values in code — config only
- [ ] No new service, datastore or dependency without an ADR
- [ ] Docs updated in this PR (README / ADR / skill), or "no doc impact" stated here
