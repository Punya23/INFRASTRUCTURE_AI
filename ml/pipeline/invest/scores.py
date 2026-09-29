"""Explainable area and city scores (spec §4, ADR-0003): config-weighted sums of observed facts.

Pure functions plus `load_config`. A factor that was not observed is dropped and the remaining
weights are renormalised — it is never scored as zero (AGENTS invariant 2, fail closed).
"""

from __future__ import annotations

import math
from collections.abc import Iterable
from dataclasses import dataclass, field
from itertools import pairwise
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
CONFIG_PATH = ROOT / "config" / "scoring.yaml"


@dataclass(frozen=True)
class Factor:
    id: str
    group: str  # "access" | "momentum"
    unit: str
    better: str  # "lower" | "higher" — display metadata; the direction lives in `bands`
    bands: tuple[tuple[float, float], ...]  # (raw value, sub-score) knots, raw value ascending
    headline_band_km: float | None


@dataclass(frozen=True)
class Preset:
    id: str
    weights: dict[str, float]
    default: bool


@dataclass(frozen=True)
class ScoringConfig:
    factors: dict[str, Factor]
    presets: dict[str, Preset]
    confidence_base: float
    max_drivers: int
    driver_min_subscore: float
    max_gaps: int
    gap_max_subscore: float
    raw: dict = field(repr=False)  # the parsed file, for grid / city settings used by other modules


@dataclass(frozen=True)
class AreaScore:
    score: float
    access: float | None
    momentum: float | None
    coverage: float
    confidence: float
    subscores: dict[str, float | None]  # echo of the inputs (None = unobserved; NaN input is stored as None)
    points: dict[str, float]  # factor -> contribution in score points; sums to `score`
    drivers: tuple[tuple[str, float], ...]  # (factor, points), largest first, at most max_drivers
    gaps: tuple[tuple[str, float], ...]  # (factor, sub-score), largest weighted shortfall first


def _validate(factors: dict[str, Factor], presets: dict[str, Preset]) -> None:
    for f in factors.values():
        xs = [x for x, _ in f.bands]
        if len(xs) < 2 or any(b <= a for a, b in pairwise(xs)):
            raise ValueError(f"factor {f.id}: band knots must be strictly ascending, got {xs}")
        if any(not 0 <= s <= 100 for _, s in f.bands):
            raise ValueError(f"factor {f.id}: band scores must be within 0-100")
        if f.group not in ("access", "momentum"):
            raise ValueError(f"factor {f.id}: unknown group {f.group!r}")
    defaults = [p.id for p in presets.values() if p.default]
    if len(defaults) != 1:
        raise ValueError(f"exactly one default preset required, got {defaults}")
    for p in presets.values():
        if set(p.weights) != set(factors):
            raise ValueError(f"preset {p.id}: weights must cover exactly {sorted(factors)}")
        if any(w < 0 for w in p.weights.values()):
            raise ValueError(f"preset {p.id}: negative weight")
        if abs(sum(p.weights.values()) - 1.0) > 1e-9:
            raise ValueError(f"preset {p.id}: weights sum to {sum(p.weights.values())}, expected 1")


def load_config(path: Path = CONFIG_PATH) -> ScoringConfig:
    raw = yaml.safe_load(Path(path).read_text())
    factors = {
        fid: Factor(
            id=fid,
            group=f["group"],
            unit=f["unit"],
            better=f["better"],
            bands=tuple((float(v), float(s)) for v, s in f["bands"]),
            headline_band_km=f.get("headline_band_km"),
        )
        for fid, f in raw["factors"].items()
    }
    presets = {
        pid: Preset(pid, {k: float(v) for k, v in p["weights"].items()}, bool(p.get("default", False)))
        for pid, p in raw["presets"].items()
    }
    _validate(factors, presets)
    d = raw["drivers"]
    return ScoringConfig(
        factors=factors,
        presets=presets,
        confidence_base=float(raw["confidence"]["base"]),
        max_drivers=int(d["max_drivers"]),
        driver_min_subscore=float(d["min_subscore"]),
        max_gaps=int(d["max_gaps"]),
        gap_max_subscore=float(d["gap_max_subscore"]),
        raw=raw,
    )


def subscore(factor: Factor, value: float | None) -> float | None:
    """Piecewise-linear 0-100 map of a raw value; None or NaN (unobserved) stays None; clamped outside the knots."""
    if value is None or math.isnan(value):
        return None
    knots = factor.bands
    if value <= knots[0][0]:
        return knots[0][1]
    for (x0, y0), (x1, y1) in pairwise(knots):
        if value <= x1:
            return y0 + (value - x0) / (x1 - x0) * (y1 - y0)
    return knots[-1][1]


def _driver_gap_lists(
    cfg: ScoringConfig,
    weights: dict[str, float],
    subs: dict[str, float],
    points: dict[str, float],
) -> tuple[tuple[tuple[str, float], ...], tuple[tuple[str, float], ...]]:
    drivers = sorted(
        ((f, p) for f, p in points.items() if subs[f] >= cfg.driver_min_subscore),
        key=lambda fp: (-fp[1], fp[0]),
    )[: cfg.max_drivers]
    gaps = sorted(
        ((f, s) for f, s in subs.items() if s < cfg.gap_max_subscore),
        key=lambda fs: (-(weights[fs[0]] * (100 - fs[1])), fs[0]),
    )[: cfg.max_gaps]
    return tuple(drivers), tuple(gaps)


def score_area(cfg: ScoringConfig, preset_id: str, subscores: dict[str, float | None]) -> AreaScore | None:
    """Score one area; None when no weighted factor was observed (nothing honest to say).

    NaN counts as not observed, exactly like None: pandas turns None into NaN in float columns."""
    unknown = set(subscores) - set(cfg.factors)
    if unknown:
        raise ValueError(f"unknown factor(s): {sorted(unknown)}")
    subs = {f: None if s is None or math.isnan(s) else s for f, s in subscores.items()}
    weights = cfg.presets[preset_id].weights
    observed = {f: s for f, s in subs.items() if s is not None and weights[f] > 0}
    observed_weight = sum(weights[f] for f in observed)
    if observed_weight == 0:
        return None
    points = {f: weights[f] * s / observed_weight for f, s in observed.items()}
    access_factors = [f for f in observed if cfg.factors[f].group == "access"]
    access_weight = sum(weights[f] for f in access_factors)
    access = (
        sum(weights[f] * observed[f] for f in access_factors) / access_weight if access_weight else None
    )
    momentum_values = [s for f, s in subs.items() if s is not None and cfg.factors[f].group == "momentum"]
    momentum = sum(momentum_values) / len(momentum_values) if momentum_values else None
    drivers, gaps = _driver_gap_lists(cfg, weights, observed, points)
    return AreaScore(
        score=sum(points.values()),
        access=access,
        momentum=momentum,
        coverage=observed_weight,  # weights sum to 1
        confidence=cfg.confidence_base * observed_weight,
        subscores=subs,
        points=points,
        drivers=drivers,
        gaps=gaps,
    )


def aggregate_city(
    cfg: ScoringConfig, preset_id: str, areas: list[AreaScore], pops: list[float]
) -> AreaScore:
    """Population-weighted city score. Per-factor points and sub-scores are weighted the same way, so
    the city's drivers add up to its score."""
    if not areas or len(areas) != len(pops):
        raise ValueError("areas and pops must be non-empty and the same length")
    total = float(sum(pops))
    if not total > 0 or any(p < 0 for p in pops):  # `not total > 0` also rejects NaN
        raise ValueError("area populations must be non-negative and sum to more than zero")
    weights = cfg.presets[preset_id].weights

    def wmean(pairs: Iterable[tuple[float | None, float]]) -> float | None:
        pairs = [(v, p) for v, p in pairs if v is not None]
        w = sum(p for _, p in pairs)
        return sum(v * p for v, p in pairs) / w if w else None

    seen = {f for a in areas for f in a.points}  # factors at least one area observed and weighted
    points = {  # config order, not set order, so a rerun writes byte-identical output
        f: sum(p * a.points.get(f, 0.0) for a, p in zip(areas, pops)) / total for f in cfg.factors if f in seen
    }
    subs = {f: wmean((a.subscores.get(f), p) for a, p in zip(areas, pops)) for f in cfg.factors}
    coverage = sum(a.coverage * p for a, p in zip(areas, pops)) / total
    observed = {f: s for f, s in subs.items() if s is not None and f in points}
    drivers, gaps = _driver_gap_lists(cfg, weights, observed, {f: points[f] for f in observed})
    return AreaScore(
        score=sum(a.score * p for a, p in zip(areas, pops)) / total,
        access=wmean((a.access, p) for a, p in zip(areas, pops)),
        momentum=wmean((a.momentum, p) for a, p in zip(areas, pops)),
        coverage=coverage,
        confidence=cfg.confidence_base * coverage,
        subscores=subs,
        points=points,
        drivers=drivers,
        gaps=gaps,
    )
