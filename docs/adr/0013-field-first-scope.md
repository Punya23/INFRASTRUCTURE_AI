# ADR-0013: Field-first scope — national highways and metro rail first, then one field at a time

- Status: Accepted
- Date: 2026-09-28
- Deciders: project team
- Supersedes: ADR-0001
- Related: README §4, §13 · ADR-0002, ADR-0004 · [`docs/fields/`](../fields/README.md) · skill `add-field`

## Context

The team is four people: two build the UI, two own data. ADR-0001 proposed every layer for two pilot cities, which spreads two data people across a dozen layers and makes nobody the expert on any of them. The team would rather finish a few infrastructure types properly — data, EDA, geospatial analysis, written findings, map layers — and add more once those are done.

## Decision

- Build **field by field**. A field is one type of infrastructure, covered for all of India, owned end to end by one person: sources → canonical tables → EDA → geospatial analysis → findings → map layers and API sections → cited pipeline of its projects.
- **Field 1 — National Highways:** NH network including expressways, lanes, toll plazas, the NH project pipeline including land-acquisition notifications, and safety. Owner: Punya.
- **Field 2 — Metro rail:** metro, RRTS and monorail — lines, stations, pipeline, ridership, station catchments and TOD zones. Owner: the second data teammate.
- When both meet the done bar in `docs/fields/README.md`, start the next field. Candidates: railways, airports, water (canals, irrigation), health, education. Every field follows the same template and skill `add-field`.
- Shared parts are built once and reused by every field: H3 grid and population (ADR-0004), growth layers (GHSL, VIIRS, Open Buildings), news AI (ADR-0008), the pin API and brief.
- Field logic lives in `ml/fields/<field>/`, field parameters in `config/fields/<field>.yaml`; shared code never special-cases a field. Each field may set its own H3 resolution (ADR-0004 already makes it configurable).
- The cities from ADR-0002 become the demo's showcase cities; they no longer bound the data.

## Consequences

- Good: clear ownership; national coverage from day one; each field is demonstrably complete instead of many thin layers; UI and data work in parallel against a fixed layer contract; "add a field" becomes the scaling story.
- Bad: cross-sector gap analysis (for example hospital or school access) waits for those fields; citizen-demand hotspots cover transport categories first; project recommendations start with two infrastructure types. Mitigation: keep the field template cheap, so field #3 lands quickly.

## Alternatives considered

- T-shaped, every layer for two cities (ADR-0001) — two people cannot clean a dozen layers well; no field would be finished.
- One owner per city — duplicates the learning curve of every layer in every city.
- Rural drinking water first (the gap report's suggestion) — valuable, but the team's focus and pitch are transport infrastructure; water is a candidate for field #3.

## Revisit when

Both fields meet the done bar (then start the next field), or the judging criteria turn out to weight social infrastructure over transport.
