# ADR-0003: Explainable indices and spatial statistics — no predictive model

- Status: Accepted
- Date: 2026-09-28
- Deciders: project team
- Related: README §8.3, §14 · ADR-0004, ADR-0008 · skill `change-scoring`

## Context

Team direction: we do not need a predictive model; we need an analytic model that brings the scattered data into one platform and explains it. Policymakers need reasoning they can audit and defend. Ground truth for "future development" is sparse and biased, so a predictive model would be hard to validate in the time available and easy to misuse as investment advice.

## Decision

- Four indices per H3 cell, rolled up to wards and districts: **Access Gap, Citizen Demand, Growth Momentum, Priority**. Each is a transparent weighted sum or percentile of observable facts. Every parameter lives in `config/scoring.yaml` with its basis documented, and every row stores its top `drivers`.
- **Hotspots** use Getis-Ord Gi* with FDR correction (PySAL `esda`).
- **"The future"** means the documented pipeline — projects with stages and evidence — never a forecast. Growth Momentum is a leading-indicator composite and is labeled as such.
- Machine learning is used only for language tasks: speech recognition, translation, classification, extraction (ADR-0008).
- Validation uses retro-checks (momentum "as of 2015" against later built-up growth) and weight-sensitivity analysis — not predictive accuracy.

## Consequences

- Good: every number can answer "why?"; easy to audit, tune and explain in a demo; fast to build.
- Bad: weights are judgment calls — mitigated by documented bases, sensitivity analysis and drivers shown in the UI. No probabilistic forecasts; they are out of scope by design.

## Alternatives considered

- A gradient-boosted model predicting built-up growth or prices — needs labels we don't have, is opaque, and invites misuse as investment advice.
- Descriptive dashboards without indices — no prioritization, so it fails "recommend high-priority projects".

## Revisit when

Several years of platform data with outcomes (resolved issues, completed projects) exist that could support a validated model — as a new ADR.
