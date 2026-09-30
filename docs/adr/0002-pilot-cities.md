# ADR-0002: Pilot cities — Bengaluru and Lucknow

- Status: Proposed
- Date: 2026-09-28
- Deciders: project team
- Related: docs/PLAN.md §4 · ADR-0001, ADR-0009 · skill `onboard-city` · ADR-0013 (makes these the demo's showcase cities; data is no longer bounded by city)

## Context

The two deep cities (ADR-0001) must: use different languages and scripts, to prove multilingual intake; have many active or announced projects, so the news layer is rich; have good OpenStreetMap and open-data coverage; and differ in type, to show the method generalizes.

## Decision

- **Bengaluru** — Tier-1 metro; Kannada, English, Hindi; dense OSM; an active civic open-data community (OpenCity, DataMeet); many live metro, suburban-rail and ring-road projects and fast growth along the airport corridor.
- **Lucknow** — Tier-2 state capital; Hindi and Urdu; an expressway hub with metro and a ring road; Hindi-heavy intake.

Both cities appear in RBI's city-level House Price Index, which lets us sanity-check Growth Momentum at city level (never per locality).

## Consequences

- Good: two scripts (Kannada, Devanagari) plus Urdu; a Tier-1 vs Tier-2 contrast; strong data communities.
- Bad: Bengaluru's municipal restructuring (BBMP to the Greater Bengaluru Authority and new corporations) means ward boundaries may be in flux — always record the boundary source and its as-of date. Lucknow has thinner civic open data, so it needs more manual curation of anchor projects.

## Alternatives considered

- Pune (Marathi), Hyderabad (Telugu), Ahmedabad (Gujarati), Indore (Hindi, Tier-2) — all viable; prefer one if the team has local knowledge or data access.
- Delhi or Mumbai — too large and too multi-agency for a first pilot.

## Revisit when

The organizers mandate cities, or the team secures better data access elsewhere. Swapping is a config change (skill `onboard-city`) plus a superseding ADR.
