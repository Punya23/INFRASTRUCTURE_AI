# ADR-0014: Use NHAI Datalake GeoServer data for analysis; publish aggregates only

- Status: Accepted
- Date: 2026-09-29
- Deciders: project team (NH field owner, 2026-09-28)
- Related: README §18 · ADR-0011, ADR-0012 · `config/sources.yaml` (`nhai_*`) · skill `add-data-source`

## Context

NHAI's public GeoServer (`datalakew.nhai.gov.in`) serves layers no other source has: NH stretches with lane status and completion targets, 678 toll plazas, 91,508 crash points (2020–23), a black-spot register with rectification status, and project stages. It states no license, so skill `add-data-source` would block it. The field owner decided to use it.

## Decision

- **Read-only:** only WFS `GetFeature` requests; nothing that could write, even though the server advertises transactional operations.
- **Keep-lists at fetch time:** each layer keeps only the fields the analysis needs; engineer names and contacts, FIR and site-visit fields are never written to disk; land-parcel layers are never fetched (ADR-0011).
- **Aggregates only in git:** raw and processed NHAI data stay under `data/` (gitignored). Committed outputs — notebooks, reports, fixtures — contain only aggregates (state tables, rates), never NHAI geometry or records. Map geometry for the UI comes from OpenStreetMap.
- **Attribution and follow-up:** every output that uses it credits NHAI; the team asks NHAI/MoRTH for terms, and deletes and rebuilds without it if refused.

## Consequences

- Good: lane status, completion targets and crash data make the safety, lane-mix and pipeline analyses possible.
- Bad: legal terms are unknown; the data is a snapshot of about 2023 from an undocumented server that may change or disappear.

## Alternatives considered

- Skip it — safety and pipeline analysis would rest on state-level PDF tables only.
- Publish the raw layers — redistribution without terms.

## Revisit when

NHAI or MoRTH states terms, or the server's layers change or disappear.
