# ADR-0012: Licensing and open standards

- Status: Proposed
- Date: 2026-09-28
- Deciders: project team
- Related: docs/PLAN.md §5, §15 · ADR-0007, ADR-0011 · skill `add-data-source`

## Context

The DPG Standard asks for an approved open license, platform independence, a way to extract data in non-proprietary formats, and adherence to standards. Our inputs carry obligations: OpenStreetMap is ODbL (share-alike), government data is GODL-India (attribution), and many scientific datasets are CC BY 4.0 (attribution). Government systems must be able to consume our outputs.

## Decision

- **Code:** Apache-2.0. **Docs:** CC BY 4.0.
- **Data exports:** OSM-derived databases under ODbL; other derived outputs under CC BY 4.0; an attribution file covering every source, generated from the source manifests.
- **Standards:** OpenAPI 3.1; GeoJSON, GeoParquet and CSV exports; Mapbox Vector Tiles; Open311 GeoReport v2 for citizen requests (Should); LGD codes for administrative units; BCP-47 language tags; ISO 8601 dates; H3 cell ids; EPSG:4326.
- **No mandatory proprietary dependency** without a documented open alternative (ADR-0007, ADR-0008, ADR-0009, ADR-0010).

## Consequences

- Good: eligible for DPG registration; others can reuse the code and data.
- Bad: ODbL share-alike limits closed reuse of OSM-derived data; attribution needs bookkeeping per source.

## Alternatives considered

- MIT for code — also DPG-approved; Apache-2.0 chosen for its explicit patent grant.
- AGPL — stronger copyleft may deter government and partner reuse.

## Revisit when

A deploying agency mandates a specific license under its open-source policy.
