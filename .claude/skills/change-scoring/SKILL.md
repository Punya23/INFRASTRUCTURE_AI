---
name: change-scoring
description: Use when changing any INFRA-AI index, weight, norm, reach/decay distance, stage weight, hotspot parameter or recommendation rule — anything in config/scoring.yaml or the scoring and hotspot code. Keeps scores explainable, config-driven and checked for robustness.
---

# Change scoring

Read first: ADR-0003 (explainable analytics, no prediction) · README §8.3 (formulas) · `AGENTS.md` invariants 4 and 8.
Paths follow README §12; if one does not exist yet, create it there.

## Rules

- Scores are weighted sums and percentiles of observable facts. No trained predictors, no black boxes.
- Every number lives in `config/scoring.yaml` with a comment giving its basis: a URDPFI norm, an agency guideline, or "team judgment, <date>".
- Every score row writes `drivers` (top contributing factors with their values). If a change makes "why?" unanswerable, it does not ship.
- City-specific overrides go in `config/cities/*.yaml`, never in code.

## Workflow

1. Edit `config/scoring.yaml` (weights, norms) or `ml/pipeline/scores.py` (formula).
2. Unit-test on a tiny synthetic grid where the right answer is obvious — for example, a hexagon far from any hospital with many reports must rank first. Keep it fast.
3. Run notebook `07_sensitivity` for both pilot cities: ±20 % weight perturbation (1,000 draws) → top-10 stability; before/after maps; rank changes among the top 20 zones. Put the summary in the PR.
4. Re-run hotspots and check that the face-validity list (independently known problem areas) still behaves.
5. Changed what an index *means* (a new component, a new normalization)? Update README §8.3 and write an ADR. Pure weight or norm tuning needs only the PR summary.
