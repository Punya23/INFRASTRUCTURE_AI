# ADR-0001: T-shaped data scope — every layer for two pilot cities, backbone networks for all of India

- Status: Superseded by ADR-0013
- Date: 2026-09-28
- Deciders: project team
- Related: docs/PLAN.md §4, §17 · ADR-0002, ADR-0004

## Context

The problem statement asks us to combine citizen feedback, demographics, infrastructure indices and investment plans, surface demand hotspots and recommend projects. Indian infrastructure data is fragmented, so cleaning is the main cost, and time is limited. Two scopes were proposed:

- **A — breadth:** 2–3 network layers (national highways, metro, railways) for every city.
- **B — depth:** every available layer for two cities.

A gap or a hotspot needs co-located layers — we cannot say an area lacks hospitals unless hospitals are loaded — so A alone cannot produce the core outputs. B alone has no national story, and "does it scale?" is the first question reviewers will ask.

## Decision

Build a T:

- **Deep:** every layer (transport, social, utilities, economic/private, context), plus news, projects and citizen intake, for two pilot cities (ADR-0002).
- **Wide:** national backbone networks for all of India — expressways and national highways, rail lines and stations, airports, metro systems — from the OpenStreetMap India extract.
- Everything city-specific lives in `config/cities/<city>.yaml`. Adding a city must not require a code change (`AGENTS.md` invariant 8).

## Consequences

- Good: the core outputs (gaps, hotspots, recommendations, rich pin briefs) are demonstrable; the backbone is nearly free and explains peripheral growth along ring roads and expressways; scale is shown by the config-driven pipeline.
- Bad: at demo time, deep analysis exists for two cities only; national views are limited to the backbone, population and rollups; keeping pilot specifics out of code takes constant discipline.

## Alternatives considered

- A only — cannot compute gaps or priorities; thin briefs.
- B only — no national view; a weak scalability story.
- Deep layers for five or more cities — the cleaning effort exceeds the available time.

## Revisit when

A third city onboards in under a day (then widen), or national datasets (for example, PM GatiShakti access) make breadth cheap.
