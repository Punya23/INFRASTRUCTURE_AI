# Investor onboarding — implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A visitor picks a state, sees its top-5 cities with reasons, opens a city to see its best areas on a map, and sees other cities compared — every number explained, no returns or forecasts.

**Architecture:** A Python pipeline (`ml/pipeline/invest`) turns raw data into JSON fixtures in `web/fixtures/invest/`; a Go stdlib API (`api/`) loads them into memory and serves `/v1/...`; static pages in `web/invest/` fetch from the API. Three tracks with disjoint files — D (pipeline), A (API), W (web) — plus lead integration.

**Tech Stack:** Python 3.12 (uv, h3, duckdb, rasterio, shapely, geopandas, pandas, numpy, pyyaml — all installed), Go 1.26 stdlib only, vanilla ES modules + MapLibre GL 4.7.1, existing `web/i18n.js`. No new dependency anywhere.

**Spec:** `docs/superpowers/specs/2026-09-29-investor-onboarding-design.md` — read it first; contracts in §4–§8 are binding.

> **Status (2026-09-30):** implemented. The code blocks below are the initial versions; review rounds and real-data runs changed them (fail-closed store validation, config-held thresholds, twin-station merge, nullable asset names, CORS origin validation, and more). The committed code is authoritative; this plan is kept as the record of intent and task order.

## Global Constraints

- **No returns, price, rent, yield or forecast numbers anywhere.** The words return(s), ROI, yield, profit, appreciation, guaranteed never appear in `web/invest/` or in `inv.*` locale keys. Every result page shows: "Scores describe existing infrastructure and past growth. They are not forecasts, price predictions or financial advice."
- Go **stdlib only**; no new Python dependency; no new service or datastore (AGENTS invariant 12).
- Every number in `config/scoring.yaml` carries a comment with its basis (a norm, a source, or "team judgment, 2026-09-29").
- Fixtures in `web/fixtures/invest/`: each file ≤ 5 MB, directory ≤ 25 MB on disk, `areas/*.geojson.gz` and `assets/*.json.gz` gzip level 9; provenance (`source`, `source_ref`, `fetched_at`, `license`, `confidence`) on every record; coordinates 4 decimals; scores, sub-scores and raw values 1 decimal; a missing value is `null`, never `0`.
- H3 resolution 7; city = urban centre ∩ state with ≥ 100,000 people (UN Degree of Urbanisation, ≥ 1,500 people/km², 8-connected); `min_area_population` 1,000; `best_area_min_population` 5,000; tiers metro ≥ 2,500,000, large ≥ 1,000,000.
- API errors are always `{"error":{"code","message"}}` with `bad_request` 400, `not_found` 404, `rate_limited` 429, `internal` 500; state codes match `^[A-Z]{2}$`, city ids `^[a-z0-9-]{2,64}$`; ids are looked up in memory, never used to build a path.
- No state or country outline is drawn anywhere (ADR-0007); DataMeet polygons are used only for point-in-polygon.
- UI strings live in `web/locales/{en,hi,kn}.json` under `inv.*`; page text is set with `textContent`/`setAttribute`, never `innerHTML` with data. Pages load code only through `<script type="module" src=…>` (plus the classic `../i18n.js` and MapLibre from unpkg): no inline scripts, no inline event handlers (`ml/tests/test_invest_copy.py` enforces this).
- Python: 3.12, type hints, ruff (line length 100), pytest, functions behind a thin CLI. Go: `slog`, `context` timeouts, table-driven tests. Config: YAML.
- **Commit rules for every agent:** small commits, one concern each; message says what and why and ends with `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`; stage **only your own paths** (`git add <paths>`, never `-A`); if `.git/index.lock` exists another track is committing — wait 3 s and retry; **never push, never stash, never touch files outside your track.**

## Review Focus

The five inputs most likely to bite a real user that no straight-line task would exercise; each has a test in the task that owns the code.

1. **A state with fewer than five cities, or none** (Goa, Sikkim, Ladakh…) — API answers 200 with `total` 0–4; the UI says "Only N cities above 1 lakh people" or shows an honest empty state; never a 404 page or a blank card row. → A2 (`TestStateCities_noCities`), W4 browser check.
2. **A factor that was not observed** for an area or city (no GHSL pixel, no station data) — dropped from the score, coverage falls, the UI shows "—", never `0`, `NaN` or `null`. → D1 (`test_missing_factor_is_dropped_not_zero`), W1 (`formatValue`).
3. **Same name in two states, and alias search** (Aurangabad; searching "Thane" must find Mumbai's region) — distinct ids, state shown next to the name. → D2 (`test_make_slugs`), A2 (`TestSearch`).
4. **Hostile or odd query input** (1 character, 200 characters, Devanagari, `<script>`, `../../etc/passwd`, SQL-like text) — 400 for too short or too long, Devanagari works, output is escaped, no path is built from input. → A2 (`TestSearch_badInput`, `TestCity_badID`), W1 (`h()` escapes).
5. **API slow, down or blocked by CORS** — every fetch times out at 8 s and shows an error state with Retry; the last good view stays on screen. → W1 (`api.test.mjs`), W5 browser check with the API stopped.

## Environment (all tracks)

Worktree root: `/Users/punyasurana/Documents/INFRA_AI/.claude/worktrees/investment-location-onboarding-13e239` (always use absolute paths; do not `cd` to the main checkout). Raw and processed data are symlinked read-only into `data/raw` and `data/processed/{national_highways,public_transport}`; new pipeline outputs go to the real directory `data/processed/invest/`. Python: `cd ml && uv run pytest && uv run ruff check .` (74 tests pass at the start). Go: `go -C api test ./...`. Web dev servers: `preview_start` name `web` (port 8765, `python3 -m http.server`) and name `api` (port 8080, added in A3).

---

# Track D — pipeline (`ml/pipeline/invest/`, `config/`)

Layout (no `__init__.py`, like the rest of `ml/`): `ml/pipeline/invest/{scores,cities,osm,geo,facts,export,__main__}.py`, `ml/fields/national_highways/cell_facts.py`, `ml/fields/public_transport/cell_facts.py`, tests `ml/tests/test_invest_*.py`. CLI: `cd ml && uv run python -m pipeline.invest osm|cities|facts|export|sensitivity|all`.

### Task 1 (D1): scoring config and pure scoring

**Files:**
- Create: `config/scoring.yaml`, `config/states.yaml`, `ml/pipeline/invest/scores.py`
- Test: `ml/tests/test_invest_scores.py`

**Interfaces:**
- Produces (later tasks import these exact names): `Factor`, `Preset`, `ScoringConfig` (`.factors`, `.presets`, `.confidence_base`, `.max_drivers`, `.driver_min_subscore`, `.max_gaps`, `.gap_max_subscore`, `.raw`), `AreaScore` (`.score .access .momentum .coverage .confidence .subscores .points .drivers .gaps`), `load_config(path=CONFIG_PATH) -> ScoringConfig`, `subscore(factor, value) -> float | None`, `score_area(cfg, preset_id, subscores) -> AreaScore | None`, `aggregate_city(cfg, preset_id, areas, pops) -> AreaScore`.

- [ ] **Step 1: Write `config/scoring.yaml`** exactly:

```yaml
# Investor onboarding scores — docs/superpowers/specs/2026-09-29-investor-onboarding-design.md.
# Every number states its basis. Scores describe observed infrastructure and past growth;
# nothing here is a forecast (ADR-0003).

grid:
  h3_res: 7                       # ≈5.2 km²; matches the 1 km WorldPop and GHSL rasters, so no false precision — spec §5
  buffer_rings: 3                 # rings of cells kept around the urban centre (≈6 km): the fringe where growth spills over — team judgment, 2026-09-29
  min_area_population: 1000       # people; below this a cell is empty farmland, not an "area" — team judgment, 2026-09-29
  best_area_min_population: 5000  # ≈1,000 people/km²: a built-up neighbourhood — team judgment, 2026-09-29

cities:
  min_population: 100000          # README §4: cities of one lakh and above
  urban_centre:
    min_density_per_km2: 1500     # UN Degree of Urbanisation (2020), urban-centre density threshold
    connectivity: 8               # 8-connected cells; the UN method uses 4-connectivity plus gap filling — team judgment, 2026-09-29
  tiers:
    metro_min_population: 2500000 # ≈ the 15 largest urban centres — team judgment, 2026-09-29
    large_min_population: 1000000 # ten lakh — team judgment, 2026-09-29
  name_overrides: {}              # geonameid: "Display name" — only after reviewing data/processed/invest/review_pieces.csv (spec §5)

confidence:
  base: 0.8                       # community (OSM) and modelled (WorldPop, GHSL) sources — team judgment, 2026-09-29

drivers:
  max_drivers: 3                  # three "why" chips fit a card — UI judgment, 2026-09-29
  min_subscore: 50                # a driver must score at least middling — team judgment, 2026-09-29
  max_gaps: 2                     # one or two watch-outs are readable — UI judgment, 2026-09-29
  gap_max_subscore: 40            # below this a factor is a watch-out — team judgment, 2026-09-29

factors:
  nh_access:
    group: access
    unit: km
    better: lower
    headline_band_km: 10          # config/fields/national_highways.yaml access_target_km
    bands: [[0, 100], [2, 90], [5, 70], [10, 40], [25, 0]]   # 2 km = local access, 10 km ≈ 20-minute drive, 25 km = out of reach — team judgment, 2026-09-29
  rail_access:
    group: access
    unit: km
    better: lower
    headline_band_km: 2           # walk or short auto ride to a suburban or main-line station — team judgment, 2026-09-29
    bands: [[0, 100], [1, 90], [3, 65], [8, 25], [15, 0]]    # team judgment, 2026-09-29
  metro_access:
    group: access
    unit: km
    better: lower
    headline_band_km: 2           # 800 m walk to ≈2 km by feeder: transit-oriented-development catchments
    bands: [[0, 100], [1, 90], [2, 70], [5, 30], [10, 0]]    # team judgment, 2026-09-29
  road_strength:
    group: access
    unit: km_per_km2
    better: higher
    headline_band_km: null
    bands: [[0, 0], [0.3, 30], [1, 65], [2, 90], [3, 100]]   # trunk + primary + secondary km per km²; measured national percentiles to be recorded here after the first run — team judgment, 2026-09-29
  built_up_growth:
    group: momentum
    unit: pp
    better: higher
    headline_band_km: null
    bands: [[0, 0], [3, 30], [10, 60], [25, 90], [40, 100]]  # percentage-point change in built-up share 2000→2020 (GHSL); measured percentiles to be recorded here after the first run — team judgment, 2026-09-29

presets:                          # weights order: nh, rail, metro, roads, growth; each row sums to 1 — team judgment, 2026-09-29
  balanced: {default: true, weights: {nh_access: 0.25, rail_access: 0.15, metro_access: 0.15, road_strength: 0.15, built_up_growth: 0.30}}
  commuter: {weights: {nh_access: 0.10, rail_access: 0.25, metro_access: 0.30, road_strength: 0.10, built_up_growth: 0.25}}
  highway:  {weights: {nh_access: 0.45, rail_access: 0.05, metro_access: 0.00, road_strength: 0.20, built_up_growth: 0.30}}
  growth:   {weights: {nh_access: 0.15, rail_access: 0.10, metro_access: 0.10, road_strength: 0.10, built_up_growth: 0.55}}
```

- [ ] **Step 2: Write `config/states.yaml`** — the 36 states and UTs with ISO 3166-2:IN codes; names must equal `pipeline.shared_layers.CANONICAL_STATES`:

```yaml
# ISO 3166-2:IN codes for the 36 states and union territories (basis: ISO 3166-2:IN).
states:
  - {code: AN, name: Andaman and Nicobar Islands}
  - {code: AP, name: Andhra Pradesh}
  - {code: AR, name: Arunachal Pradesh}
  - {code: AS, name: Assam}
  - {code: BR, name: Bihar}
  - {code: CH, name: Chandigarh}
  - {code: CG, name: Chhattisgarh}
  - {code: DH, name: Dadra and Nagar Haveli and Daman and Diu}
  - {code: DL, name: Delhi}
  - {code: GA, name: Goa}
  - {code: GJ, name: Gujarat}
  - {code: HR, name: Haryana}
  - {code: HP, name: Himachal Pradesh}
  - {code: JK, name: Jammu and Kashmir}
  - {code: JH, name: Jharkhand}
  - {code: KA, name: Karnataka}
  - {code: KL, name: Kerala}
  - {code: LA, name: Ladakh}
  - {code: LD, name: Lakshadweep}
  - {code: MP, name: Madhya Pradesh}
  - {code: MH, name: Maharashtra}
  - {code: MN, name: Manipur}
  - {code: ML, name: Meghalaya}
  - {code: MZ, name: Mizoram}
  - {code: NL, name: Nagaland}
  - {code: OD, name: Odisha}
  - {code: PY, name: Puducherry}
  - {code: PB, name: Punjab}
  - {code: RJ, name: Rajasthan}
  - {code: SK, name: Sikkim}
  - {code: TN, name: Tamil Nadu}
  - {code: TG, name: Telangana}
  - {code: TR, name: Tripura}
  - {code: UP, name: Uttar Pradesh}
  - {code: UK, name: Uttarakhand}
  - {code: WB, name: West Bengal}
```

- [ ] **Step 3: Write the failing tests** `ml/tests/test_invest_scores.py`:

```python
import pytest
import yaml

from pipeline.invest.scores import (
    CONFIG_PATH,
    Factor,
    aggregate_city,
    load_config,
    score_area,
    subscore,
)
from pipeline.shared_layers import CANONICAL_STATES

FACTORS = ("nh_access", "rail_access", "metro_access", "road_strength", "built_up_growth")
ALL_80 = {f: 80.0 for f in FACTORS}
NH = Factor("nh_access", "access", "km", "lower", ((0, 100), (2, 90), (5, 70), (10, 40), (25, 0)), 10)


@pytest.fixture(scope="module")
def cfg():
    return load_config()


@pytest.mark.parametrize(
    ("value", "expected"),
    [(0, 100), (2, 90), (5, 70), (10, 40), (25, 0), (3.5, 80.0), (-1, 100), (400, 0)],
)
def test_subscore_hits_every_knot_interpolates_and_clamps(value, expected):
    assert subscore(NH, value) == pytest.approx(expected)


def test_unobserved_stays_unobserved():
    assert subscore(NH, None) is None
    assert subscore(NH, float("nan")) is None


def test_config_matches_spec(cfg):
    assert set(cfg.factors) == set(FACTORS)
    assert set(cfg.presets) == {"balanced", "commuter", "highway", "growth"}
    assert cfg.presets["balanced"].default
    assert all(sum(p.weights.values()) == pytest.approx(1.0) for p in cfg.presets.values())


def test_load_config_rejects_weights_that_do_not_sum_to_one(tmp_path):
    raw = yaml.safe_load(CONFIG_PATH.read_text())
    raw["presets"]["balanced"]["weights"]["nh_access"] = 0.5
    bad = tmp_path / "scoring.yaml"
    bad.write_text(yaml.safe_dump(raw))
    with pytest.raises(ValueError, match="sum"):
        load_config(bad)


def test_states_yaml_matches_canonical_states():
    states = yaml.safe_load((CONFIG_PATH.parent / "states.yaml").read_text())["states"]
    assert sorted(s["name"] for s in states) == sorted(CANONICAL_STATES)
    codes = [s["code"] for s in states]
    assert len(set(codes)) == len(codes) == 36 and all(len(c) == 2 and c.isupper() for c in codes)


def test_all_observed_full_coverage(cfg):
    r = score_area(cfg, "balanced", ALL_80)
    assert r.score == pytest.approx(80.0)
    assert r.coverage == pytest.approx(1.0)
    assert r.confidence == pytest.approx(0.8)
    assert sum(r.points.values()) == pytest.approx(r.score)


def test_missing_factor_is_dropped_not_zero(cfg):
    r = score_area(cfg, "balanced", {**ALL_80, "metro_access": None})
    assert r.score == pytest.approx(80.0)  # a zero would have dragged it to 68
    assert r.coverage == pytest.approx(0.85)  # balanced weight of metro_access is 0.15
    assert r.confidence == pytest.approx(0.8 * 0.85)
    assert "metro_access" not in r.points


def test_zero_weight_factor_does_not_lower_coverage(cfg):
    r = score_area(cfg, "highway", {**ALL_80, "metro_access": None})
    assert r.coverage == pytest.approx(1.0)
    assert r.score == pytest.approx(80.0)


def test_nothing_observed_returns_none(cfg):
    assert score_area(cfg, "balanced", {f: None for f in FACTORS}) is None


def test_unknown_factor_is_rejected(cfg):
    with pytest.raises(ValueError, match="unknown factor"):
        score_area(cfg, "balanced", {**ALL_80, "vibes": 90.0})


def test_access_momentum_drivers_and_gaps(cfg):
    subs = {"nh_access": 90, "rail_access": 10, "metro_access": 0, "road_strength": 60, "built_up_growth": 100}
    r = score_area(cfg, "balanced", subs)
    assert r.score == pytest.approx(63.0)  # 22.5 + 1.5 + 0 + 9 + 30
    assert r.access == pytest.approx(33.0 / 0.70)
    assert r.momentum == pytest.approx(100.0)
    assert [f for f, _ in r.drivers] == ["built_up_growth", "nh_access", "road_strength"]
    assert r.drivers[0][1] == pytest.approx(30.0)
    assert [f for f, _ in r.gaps] == ["metro_access", "rail_access"]  # 0.15*100 then 0.15*90


def test_city_is_population_weighted(cfg):
    a = score_area(cfg, "balanced", ALL_80)
    b = score_area(cfg, "balanced", {f: 40.0 for f in FACTORS})
    c = aggregate_city(cfg, "balanced", [a, b], [3000, 1000])
    assert c.score == pytest.approx(70.0)
    assert sum(c.points.values()) == pytest.approx(c.score)
    assert c.subscores["nh_access"] == pytest.approx(70.0)


def test_city_points_reconcile_when_areas_miss_different_factors(cfg):
    a = score_area(cfg, "balanced", {**ALL_80, "metro_access": None})
    b = score_area(cfg, "balanced", {**ALL_80, "rail_access": 20.0})
    c = aggregate_city(cfg, "balanced", [a, b], [1000, 1000])
    assert sum(c.points.values()) == pytest.approx(c.score)
    assert c.coverage == pytest.approx((0.85 + 1.0) / 2)
    assert c.subscores["metro_access"] == pytest.approx(80.0)  # only area b observed it


def test_city_rejects_empty_and_zero_population(cfg):
    a = score_area(cfg, "balanced", ALL_80)
    with pytest.raises(ValueError):
        aggregate_city(cfg, "balanced", [], [])
    with pytest.raises(ValueError):
        aggregate_city(cfg, "balanced", [a], [0])
```

- [ ] **Step 4: Run to confirm failure.** `cd ml && uv run pytest tests/test_invest_scores.py -q` → FAIL (`ModuleNotFoundError: pipeline.invest.scores`).

- [ ] **Step 5: Write `ml/pipeline/invest/scores.py`:**

```python
"""Explainable area and city scores (spec §4, ADR-0003): config-weighted sums of observed facts.

Pure functions plus `load_config`. A factor that was not observed is dropped and the remaining
weights are renormalised — it is never scored as zero (AGENTS invariant 2, fail closed).
"""

from __future__ import annotations

from dataclasses import dataclass, field
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
    subscores: dict[str, float | None]  # echo of the inputs (None = unobserved)
    points: dict[str, float]  # factor -> contribution in score points; sums to `score`
    drivers: tuple[tuple[str, float], ...]  # (factor, points), largest first, at most max_drivers
    gaps: tuple[tuple[str, float], ...]  # (factor, sub-score), largest weighted shortfall first


def _validate(factors: dict[str, Factor], presets: dict[str, Preset]) -> None:
    for f in factors.values():
        xs = [x for x, _ in f.bands]
        if len(xs) < 2 or any(b <= a for a, b in zip(xs, xs[1:])):
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
    if value is None or value != value:
        return None
    knots = factor.bands
    if value <= knots[0][0]:
        return knots[0][1]
    for (x0, y0), (x1, y1) in zip(knots, knots[1:]):
        if value <= x1:
            return y0 + (value - x0) / (x1 - x0) * (y1 - y0)
    return knots[-1][1]


def _driver_gap_lists(cfg, weights, subs, points):
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
    """Score one area; None when no weighted factor was observed (nothing honest to say)."""
    unknown = set(subscores) - set(cfg.factors)
    if unknown:
        raise ValueError(f"unknown factor(s): {sorted(unknown)}")
    weights = cfg.presets[preset_id].weights
    observed = {f: s for f, s in subscores.items() if s is not None and weights[f] > 0}
    observed_weight = sum(weights[f] for f in observed)
    if observed_weight == 0:
        return None
    points = {f: weights[f] * s / observed_weight for f, s in observed.items()}
    access_factors = [f for f in observed if cfg.factors[f].group == "access"]
    access_weight = sum(weights[f] for f in access_factors)
    access = (
        sum(weights[f] * observed[f] for f in access_factors) / access_weight if access_weight else None
    )
    momentum_values = [s for f, s in subscores.items() if s is not None and cfg.factors[f].group == "momentum"]
    momentum = sum(momentum_values) / len(momentum_values) if momentum_values else None
    drivers, gaps = _driver_gap_lists(cfg, weights, observed, points)
    return AreaScore(
        score=sum(points.values()),
        access=access,
        momentum=momentum,
        coverage=observed_weight,  # weights sum to 1
        confidence=cfg.confidence_base * observed_weight,
        subscores=dict(subscores),
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
    if total <= 0:
        raise ValueError("city population must be positive")
    weights = cfg.presets[preset_id].weights

    def wmean(pairs):
        pairs = [(v, p) for v, p in pairs if v is not None]
        w = sum(p for _, p in pairs)
        return sum(v * p for v, p in pairs) / w if w else None

    seen = {f for a in areas for f in a.points}  # factors at least one area observed and weighted
    points = {f: sum(p * a.points.get(f, 0.0) for a, p in zip(areas, pops)) / total for f in seen}
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
```

- [ ] **Step 6: Run tests and lint.** `cd ml && uv run pytest tests/test_invest_scores.py -q && uv run ruff check pipeline tests` → all pass.
- [ ] **Step 7: Commit.** `git add config/scoring.yaml config/states.yaml ml/pipeline/invest/scores.py ml/tests/test_invest_scores.py && git commit` — message `feat(invest): explainable area and city scoring with config-weighted presets`.

### Task 2 (D2): urban centres, naming, slugs, tiers

**Files:**
- Create: `ml/pipeline/invest/cities.py`
- Test: `ml/tests/test_invest_cities.py`

**Interfaces:**
- Consumes: nothing from D1 (pure numpy/pandas).
- Produces: `label_urban_centres(density, state_ids, min_density, connectivity=8) -> tuple[np.ndarray, dict[int, int]]` (labels ≥ 1, `label → state id`), `assign_places(places, labels, transform) -> DataFrame` (adds int column `label`), `name_pieces(pieces, places, overrides) -> DataFrame`, `make_slugs(names, state_codes) -> list[str]`, `tier_of(population, metro_min, large_min) -> str`.

- [ ] **Step 1: Write the failing tests** `ml/tests/test_invest_cities.py`:

```python
import numpy as np
import pandas as pd
import pytest
from affine import Affine

from pipeline.invest.cities import (
    assign_places,
    label_urban_centres,
    make_slugs,
    name_pieces,
    tier_of,
)


def test_below_threshold_is_background():
    density = np.full((3, 3), 1499.0)
    labels, label_state = label_urban_centres(density, np.ones((3, 3), int), 1500)
    assert labels.max() == 0 and label_state == {}


def test_blob_is_cut_at_state_border():
    density = np.zeros((4, 8))
    density[1:3, 1:7] = 2000
    state = np.zeros((4, 8), dtype=int)
    state[:, :4], state[:, 4:] = 1, 2
    labels, label_state = label_urban_centres(density, state, 1500)
    assert set(np.unique(labels)) == {0, 1, 2}
    assert labels[1, 1] == labels[2, 3] != labels[1, 4]
    assert sorted(label_state.values()) == [1, 2]


def test_diagonal_cells_join_only_with_8_connectivity():
    density = np.zeros((3, 3))
    density[0, 0] = density[1, 1] = 2000
    state = np.ones((3, 3), int)
    assert label_urban_centres(density, state, 1500, connectivity=8)[0].max() == 1
    assert label_urban_centres(density, state, 1500, connectivity=4)[0].max() == 2


def test_cells_outside_every_state_polygon_inherit_the_neighbour_state():
    density = np.zeros((3, 6))
    density[1, 1:5] = 2000  # a coastal city: its last two cells fall outside every polygon
    state = np.zeros((3, 6), dtype=int)
    state[1, 1:3] = 7
    labels, label_state = label_urban_centres(density, state, 1500)
    assert len(set(labels[1, 1:5])) == 1 and labels[1, 1] > 0
    assert set(label_state.values()) == {7}


def test_assign_places_uses_the_raster_cell():
    labels = np.zeros((2, 2), dtype=np.int32)
    labels[0, 0] = 5
    transform = Affine(0.1, 0, 73.0, 0, -0.1, 19.0)  # pixel (0,0) spans lon 73.0-73.1, lat 18.9-19.0
    places = pd.DataFrame({"lon": [73.05, 73.15, 80.0], "lat": [18.95, 18.95, 18.95]})
    assert assign_places(places, labels, transform)["label"].tolist() == [5, 0, 0]


def test_name_pieces_uses_largest_place_and_lists_big_aliases():
    pieces = pd.DataFrame({"label": [1, 2], "population": [900_000, 150_000]})
    places = pd.DataFrame(
        {
            "geonameid": [10, 11, 12],
            "name": ["Faridabad", "Gurugram", "Kotputli"],
            "lat": [28.40, 28.46, 27.70],
            "lon": [77.31, 77.03, 76.20],
            "population": [1_400_000, 876_000, 30_000],
            "label": [1, 1, 2],
        }
    )
    out = name_pieces(pieces, places, overrides={}).set_index("label")
    assert out.loc[1, "name"] == "Faridabad" and out.loc[1, "aliases"] == ["Gurugram"]
    assert bool(out.loc[1, "review"]) is True  # two places ≥ 100,000 in one piece: a human looks
    assert out.loc[2, "name"] == "Kotputli" and bool(out.loc[2, "review"]) is False


def test_override_promotes_the_named_place_to_anchor():
    pieces = pd.DataFrame({"label": [1], "population": [900_000]})
    places = pd.DataFrame(
        {
            "geonameid": [10, 11],
            "name": ["Faridabad", "Gurugram"],
            "lat": [28.40, 28.46],
            "lon": [77.31, 77.03],
            "population": [1_400_000, 876_000],
            "label": [1, 1],
        }
    )
    out = name_pieces(pieces, places, overrides={11: "Gurugram"}).iloc[0]
    assert out["name"] == "Gurugram" and out["aliases"] == ["Faridabad"]
    assert (out["lat"], out["lon"]) == (28.46, 77.03)


def test_piece_without_a_place_gets_no_name():
    out = name_pieces(
        pd.DataFrame({"label": [3], "population": [120_000]}),
        pd.DataFrame({"geonameid": [], "name": [], "lat": [], "lon": [], "population": [], "label": []}),
        overrides={},
    )
    assert out.iloc[0]["name"] is None


def test_make_slugs_disambiguates_by_state_then_counter():
    names = ["Aurangabad", "Aurangabad", "Pune", "Pune", "Nashik"]
    states = ["MH", "BR", "MH", "MH", "MH"]
    assert make_slugs(names, states) == ["aurangabad-mh", "aurangabad-br", "pune-mh", "pune-mh-2", "nashik"]


def test_make_slugs_are_ascii_and_api_safe():
    (slug,) = make_slugs(["São  Paulo!"], ["MH"])
    assert slug == "sao-paulo"


@pytest.mark.parametrize(
    ("population", "tier"), [(2_500_000, "metro"), (2_499_999, "large"), (1_000_000, "large"), (999_999, "mid")]
)
def test_tier_of(population, tier):
    assert tier_of(population, 2_500_000, 1_000_000) == tier
```

- [ ] **Step 2: Run to confirm failure** (`ModuleNotFoundError`). `affine` ships with rasterio.
- [ ] **Step 3: Write `ml/pipeline/invest/cities.py`:**

```python
"""City definition (spec §5): urban centres (UN Degree of Urbanisation) cut at state borders.

Pure functions; the raster and GeoNames loading lives in the CLI step that calls them.
"""

from __future__ import annotations

import re
import unicodedata
from collections import Counter

import numpy as np
import pandas as pd

_OFFSETS = {
    4: [(-1, 0), (0, -1), (0, 1), (1, 0)],
    8: [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)],
}
BIG_PLACE = 100_000  # GeoNames places at least this big are listed as aliases and trigger a review


def _fill_unknown_state(state_ids, mask, offsets, rounds=3):
    """Cells with state id 0 (coastline or simplified border) inherit the state of a neighbour."""
    state = state_ids.copy()
    h, w = state.shape
    for _ in range(rounds):
        unknown = mask & (state == 0)
        if not unknown.any():
            break
        padded = np.pad(state, 1)
        for dr, dc in offsets:
            shifted = padded[1 + dr : 1 + dr + h, 1 + dc : 1 + dc + w]
            take = unknown & (state == 0) & (shifted != 0)
            state[take] = shifted[take]
    return state


def label_urban_centres(density, state_ids, min_density, connectivity=8):
    """Label contiguous cells with density >= min_density; never let a label cross a state border.

    Returns (labels, label_state): labels are 1.. (0 = background), label_state maps label -> state id.
    """
    if density.shape != state_ids.shape:
        raise ValueError("density and state_ids must have the same shape")
    if connectivity not in _OFFSETS:
        raise ValueError("connectivity must be 4 or 8")
    mask = np.nan_to_num(density, nan=0.0) >= min_density
    offsets = _OFFSETS[connectivity]
    height, width = mask.shape
    component = np.zeros(mask.shape, dtype=np.int32)
    n = 0
    for r0, c0 in zip(*np.nonzero(mask)):
        if component[r0, c0]:
            continue
        n += 1
        component[r0, c0] = n
        stack = [(r0, c0)]
        while stack:
            r, c = stack.pop()
            for dr, dc in offsets:
                rr, cc = r + dr, c + dc
                if 0 <= rr < height and 0 <= cc < width and mask[rr, cc] and not component[rr, cc]:
                    component[rr, cc] = n
                    stack.append((rr, cc))
    state = _fill_unknown_state(state_ids, mask, offsets)
    labels = np.zeros(mask.shape, dtype=np.int32)
    keys: dict[tuple[int, int], int] = {}
    label_state: dict[int, int] = {}
    for r, c in zip(*np.nonzero(mask)):
        key = (int(component[r, c]), int(state[r, c]))
        if key not in keys:
            keys[key] = len(keys) + 1
            label_state[keys[key]] = key[1]
        labels[r, c] = keys[key]
    return labels, label_state


def assign_places(places: pd.DataFrame, labels: np.ndarray, transform) -> pd.DataFrame:
    """Add `label` (0 = outside every urban centre) to places with `lon`/`lat`, by the raster cell."""
    cols, rows = ~transform * (places["lon"].to_numpy(), places["lat"].to_numpy())
    rows, cols = np.floor(rows).astype(int), np.floor(cols).astype(int)
    inside = (rows >= 0) & (rows < labels.shape[0]) & (cols >= 0) & (cols < labels.shape[1])
    out = places.copy()
    out["label"] = 0
    out.loc[inside, "label"] = labels[rows[inside], cols[inside]]
    return out


def name_pieces(pieces: pd.DataFrame, places: pd.DataFrame, overrides: dict[int, str]) -> pd.DataFrame:
    """Name each piece after its anchor place: the largest GeoNames place inside it, or the place an
    override names. Adds name, geonameid, lat, lon, aliases (other places >= 100,000) and review
    (two or more such places). A piece with no place gets name None — the caller reviews and skips it."""
    rows = []
    for piece in pieces.itertuples():
        inside = places[places["label"] == piece.label].sort_values(
            ["population", "geonameid"], ascending=[False, True]
        )
        row = {"name": None, "geonameid": None, "lat": None, "lon": None, "aliases": [], "review": False}
        if len(inside):
            forced = inside[inside["geonameid"].isin(list(overrides))]
            anchor = (forced if len(forced) else inside).iloc[0]
            big = inside[(inside["population"] >= BIG_PLACE) & (inside["geonameid"] != anchor["geonameid"])]
            row.update(
                name=overrides.get(int(anchor["geonameid"]), anchor["name"]),
                geonameid=int(anchor["geonameid"]),
                lat=float(anchor["lat"]),
                lon=float(anchor["lon"]),
                aliases=[str(n) for n in big["name"]],
                review=bool((inside["population"] >= BIG_PLACE).sum() >= 2),
            )
        rows.append(row)
    return pd.concat([pieces.reset_index(drop=True), pd.DataFrame(rows)], axis=1)


def _slug(name: str) -> str:
    ascii_name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", ascii_name.lower()).strip("-")


def make_slugs(names: list[str], state_codes: list[str]) -> list[str]:
    """Deterministic ids: the slug; on a collision every colliding city gets `-<state>`; then `-2`, `-3`."""
    base = [_slug(n) for n in names]
    if any(len(b) < 2 for b in base):
        raise ValueError(f"names that slugify to fewer than 2 characters: {names}")
    counts = Counter(base)
    slugs = [b if counts[b] == 1 else f"{b}-{s.lower()}" for b, s in zip(base, state_codes)]
    seen: Counter = Counter()
    out = []
    for s in slugs:
        seen[s] += 1
        out.append(s if seen[s] == 1 else f"{s}-{seen[s]}")
    return out


def tier_of(population: float, metro_min: float, large_min: float) -> str:
    return "metro" if population >= metro_min else "large" if population >= large_min else "mid"
```

- [ ] **Step 4: Run tests and lint** → pass. **Step 5: Commit** `feat(invest): urban-centre labelling, piece naming, slugs and tiers`.

### Task 3 (D3): OSM nodes — stations and place names

**Files:**
- Create: `ml/pipeline/invest/osm.py`
- Test: `ml/tests/test_invest_osm.py`

**Interfaces:**
- Produces: `classify_station(tags: dict[str, str]) -> str | None` (`"metro"`, `"rail"` or None), `place_rank(place: str) -> int | None` (lower = better name), `extract() -> None` writing `data/processed/invest/osm_stations.parquet` (`node_id:int64, lon, lat, name:str|None, mode:str`) and `data/processed/invest/osm_places.parquet` (`node_id, lon, lat, name, place`).

- [ ] **Step 1: Write the failing tests** `ml/tests/test_invest_osm.py`:

```python
from pipeline.invest.osm import classify_station, place_rank


def test_classify_station():
    assert classify_station({"railway": "station"}) == "rail"
    assert classify_station({"railway": "halt"}) == "rail"
    for kind in ("subway", "light_rail", "monorail"):
        assert classify_station({"railway": "station", "station": kind}) == "metro"
    assert classify_station({"public_transport": "station", "subway": "yes"}) == "metro"
    assert classify_station({"railway": "station", "light_rail": "yes"}) == "metro"
    assert classify_station({"railway": "tram_stop"}) is None
    assert classify_station({"highway": "bus_stop"}) is None
    assert classify_station({"railway": "station", "disused": "yes"}) is None
    assert classify_station({}) is None


def test_place_rank_orders_localities_and_ignores_the_rest():
    order = ["suburb", "neighbourhood", "quarter", "village", "town", "hamlet"]
    ranks = [place_rank(p) for p in order]
    assert ranks == sorted(ranks) and len(set(ranks)) == len(order)
    assert place_rank("city") is not None and place_rank("city") > place_rank("hamlet")
    assert place_rank("farm") is None and place_rank("isolated_dwelling") is None
```

- [ ] **Step 2: Run to confirm failure.**
- [ ] **Step 3: Implement** `classify_station`, `place_rank` (suburb 1, neighbourhood 2, quarter 3, village 4, town 5, hamlet 6, city 7 — city only when nothing finer is inside a cell) and `extract()`. `extract()` follows the DuckDB pattern of `ml/fields/national_highways/build.py:extract_osm` (`ST_ReadOSM('<pbf>')`, `kind = 'node'`, tag filters on the `tags` map, same `_duckdb_tmp` spill directory): one streaming pass over `data/raw/osm/india-latest.osm.pbf` selecting nodes with `railway in (station, halt)` or `public_transport = station` (then classify in Python with `classify_station`) and nodes with a `place` tag from `place_rank` and a `name` (use `name:en` when present). Write both parquet files atomically (temp file then rename) so a re-run is idempotent. Fail closed: raise if the PBF is missing (`run: cd ml && uv run python -m common.fetch`), and after extraction assert plausible counts — rail stations 5,000–20,000, metro stations 400–2,500, places ≥ 200,000 — raising `RuntimeError` with the numbers otherwise.
- [ ] **Step 4: Run unit tests → pass. Then run the extraction once:** `cd ml && uv run python -c "from pipeline.invest.osm import extract; extract()"` (a few minutes; run it in the background while doing D4). Print counts by mode and 10 sample metro station names near Pune (lat 18.5, lon 73.85, within 0.3°) to eyeball.
- [ ] **Step 5: Commit** `feat(invest): extract OSM stations and place names for area facts`.

### Task 4 (D4): cell facts

**Files:**
- Create: `ml/pipeline/invest/geo.py`, `ml/pipeline/invest/facts.py`, `ml/fields/national_highways/cell_facts.py`, `ml/fields/public_transport/cell_facts.py`
- Test: `ml/tests/test_invest_facts.py`

**Interfaces:**
- Produces:
  - `geo.nearest_km(centres: DataFrame[lat, lon], targets: GeoSeries) -> Series` — km (EPSG:7755 metres ÷ 1000) to the nearest target; NaN when `targets` is empty.
  - `facts.cell_centres(cells: list[str]) -> DataFrame[cell, lat, lon]`; `facts.mean_by_cell(lons, lats, values, res) -> Series` (cell → mean); `facts.sum_by_cell(lons, lats, values, res) -> Series`; `facts.growth_pp(b2000_by_cell, b2020_by_cell) -> Series` = 100·(mean₂₀₂₀ − mean₂₀₀₀)/1e6; `facts.km_per_km2(km_by_cell: Series) -> Series` (÷ `h3.cell_area(cell, "km^2")`); `facts.name_cells(cells: DataFrame[cell, lat, lon], places: DataFrame[lon, lat, name, place], max_km=2.5) -> Series` (spec §5 rule; None when nothing is near).
  - `national_highways.cell_facts.nh_access_km(centres) -> Series` (operational NH and expressway segments only, from `data/processed/national_highways/nh_segments.parquet`); `.arterial_km_by_cell(res) -> Series` (NH `eff_km` apportioned over sampled points + primary/secondary context ways from `osm_context_way_nodes.parquet`, segment midpoints → cell).
  - `public_transport.cell_facts.station_access_km(centres, mode) -> Series` (OSM `osm_stations.parquet` for the mode ∪ GTFS metro stops for `mode="metro"`, de-duplicated within 150 m); `.bus_stop_counts(cells, res) -> Series` (GTFS `mode == "bus"` stops per cell); `.bus_feeds_by_cell(cells, res) -> dict` (operator, tier, license, fetched_at, stops — for cities that have a feed).

- [ ] **Step 1: Write the failing tests** `ml/tests/test_invest_facts.py`:

```python
import geopandas as gpd
import h3
import pandas as pd
import pytest
from shapely.geometry import LineString, Point

from pipeline.invest.facts import (
    growth_pp,
    km_per_km2,
    mean_by_cell,
    name_cells,
    sum_by_cell,
)
from pipeline.invest.geo import nearest_km

RES = 7


def test_nearest_km_to_a_line_and_a_point():
    centres = pd.DataFrame({"lat": [18.51, 18.50], "lon": [73.9, 73.9]})
    line = gpd.GeoSeries([LineString([(73.8, 18.5), (74.0, 18.5)])], crs="EPSG:4326")
    d = nearest_km(centres, line)
    assert d.iloc[0] == pytest.approx(1.11, abs=0.06)  # 0.01° of latitude
    assert d.iloc[1] == pytest.approx(0.0, abs=0.01)
    pts = gpd.GeoSeries([Point(73.91, 18.50)], crs="EPSG:4326")
    assert nearest_km(centres.iloc[[1]], pts).iloc[0] == pytest.approx(1.06, abs=0.06)  # 0.01° of longitude


def test_nearest_km_without_targets_is_unobserved_not_zero():
    centres = pd.DataFrame({"lat": [18.5], "lon": [73.9]})
    assert nearest_km(centres, gpd.GeoSeries([], crs="EPSG:4326")).isna().all()


def test_mean_and_sum_by_cell_group_points_by_h3_cell():
    cell = h3.latlng_to_cell(18.5, 73.8, RES)
    lons, lats, vals = [73.8, 73.8001, 90.0], [18.5, 18.5001, 10.0], [100.0, 300.0, 5.0]
    assert mean_by_cell(lons, lats, vals, RES)[cell] == pytest.approx(200.0)
    assert sum_by_cell(lons, lats, vals, RES)[cell] == pytest.approx(400.0)


def test_growth_pp_is_change_in_built_up_share():
    cell = "8760e6a5bffffff"
    b2000, b2020 = pd.Series({cell: 100_000.0}), pd.Series({cell: 300_000.0})  # m² per 1 km² pixel
    assert growth_pp(b2000, b2020)[cell] == pytest.approx(20.0)


def test_km_per_km2_divides_by_the_cell_area():
    cell = h3.latlng_to_cell(18.5, 73.8, RES)
    area = h3.cell_area(cell, "km^2")
    assert km_per_km2(pd.Series({cell: 10.0}))[cell] == pytest.approx(10.0 / area)


def test_name_cells_prefers_inside_then_rank_then_nearest_then_none():
    inside = h3.latlng_to_cell(18.55, 73.80, RES)
    outside = h3.latlng_to_cell(18.70, 73.80, RES)
    empty = h3.latlng_to_cell(19.50, 74.50, RES)
    cells = pd.DataFrame(
        [(c, *h3.cell_to_latlng(c)) for c in (inside, outside, empty)], columns=["cell", "lat", "lon"]
    )
    lat, lon = h3.cell_to_latlng(inside)
    places = pd.DataFrame(
        {
            "lon": [lon, lon + 0.002, 73.80],
            "lat": [lat, lat + 0.002, 18.71],
            "name": ["Pashan", "Baner", "Talegaon"],
            "place": ["village", "suburb", "town"],  # a suburb outranks a village inside the same cell
        }
    )
    names = name_cells(cells, places)
    assert names[inside] == "Baner"
    assert names[outside] == "Talegaon"  # nothing inside; nearest place within 2.5 km
    assert names[empty] is None
```

- [ ] **Step 2: Run to confirm failure.**
- [ ] **Step 3: Implement.**
  - `geo.nearest_km`: project centres and targets with `pipeline.shared_layers.INDIA_CRS`, build `shapely.STRtree(targets.values)`, call `tree.query_nearest(points, return_distance=True, all_matches=False)`, write distances ÷ 1000 into a NaN-filled array at the input indices. Empty targets → all-NaN Series.
  - `facts` functions per the interface (vectorised pandas: `h3.latlng_to_cell` per point, then `groupby`). `name_cells`: for each cell, candidates are places inside the cell (`h3.latlng_to_cell(place) == cell`) → best by `(place_rank, distance to centre)`; else the nearest place within `max_km` by haversine (use `nearest_km` on a GeoSeries of place points and map back to the place name — for large frames use a spatial index, not a double loop); else None. Use `pipeline.invest.osm.place_rank` for ranking.
  - `national_highways/cell_facts.py`: read `nh_segments.parquet` with geopandas/shapely (`geometry` is WKB), keep `status == "operational"` (kinds `nh_segment` and `expressway_segment`). `arterial_km_by_cell`: sample NH lines every 200 m (`shapely.line_interpolate_point`), each point worth `eff_km / n_points` km; add context ways from `osm_context_way_nodes.parquet` (sort by `way_id, pos`, consecutive-node haversine length, midpoint → cell). Use only OSM-derived geometry and attributes (ADR-0014): never read `nhai_*.parquet` here.
  - `public_transport/cell_facts.py`: as in the interface; GTFS from `data/processed/public_transport/gtfs_stops.parquet` (columns `stop_lat, stop_lon, mode, operator, tier, source, fetched_at, license`).
- [ ] **Step 4: Run tests and lint → pass. Smoke test on real data:** load the Pune centre cell set and print `nh_access_km`, `station_access_km(…, "rail"/"metro")` and `arterial_km_by_cell` for 5 cells; values must be plausible (Pune centre: rail < 3 km; NH within 15 km).
- [ ] **Step 5: Commit** `feat(invest): per-cell access, growth, road and naming facts` (one commit per module if preferred).

### Task 5 (D5): build, score, export, verify

**Files:**
- Create: `ml/pipeline/invest/export.py`, `ml/pipeline/invest/__main__.py`, `ml/tests/test_invest_export.py`, `ml/tests/test_invest_contract.py`, `ml/tests/test_invest_spotchecks.py`, `web/fixtures/invest/**` (generated)
- Modify: none outside track D.

**Interfaces:**
- Consumes: everything from D1–D4.
- Produces: the fixtures of spec §6; CLI steps `cities`, `facts`, `export`, `sensitivity`, `all`; review files `data/processed/invest/review_pieces.csv` (pieces with ≥ 2 places ≥ 100 k) and `review_unnamed_pieces.csv`.

- [ ] **Step 1: `cities` step.** Read the WorldPop GeoTIFF with rasterio (`RAW / "worldpop" / "ind_ppp_2020_1km_Aggregated_UNadj.tif"`, `RAW` from `pipeline.shared_layers`; band 1 masked → 0 is `density`, plus the affine transform), rasterize DataMeet states (`load_states`, ids 1..N in sorted order, `all_touched=True`) onto the same grid, `label_urban_centres(density, state_ids, cfg.raw["cities"]["urban_centre"]["min_density_per_km2"], connectivity)`. Per label: population = Σ density (a WorldPop 1 km cell holds ≈ 1 km²), pop-weighted centroid. Keep `population ≥ cities.min_population`. Load GeoNames places with `pipeline.shared_layers.load_cities(min_population=15_000)` (columns `geonameid, name, lat, lon, population`; `name` is the ASCII name), `assign_places`, `name_pieces` with `cities.name_overrides`, then drop unnamed pieces into `review_unnamed_pieces.csv`, write `review_pieces.csv`, compute `id` (`make_slugs`), `state` code (from `config/states.yaml` via the label's state name), `tier`. Save `data/processed/invest/pieces.parquet`. Print a summary: cities per state, top 10 by population, and every piece flagged `review`.
- [ ] **Step 2: `facts` step.** For each city piece: cells = H3 res-7 cells covering the piece's raster cells (centre → cell), expanded by `buffer_rings` (`h3.grid_disk`), union over all cities for computation. Per unique cell compute: `pop` (WorldPop points → `sum_by_cell`), `built_up_growth` (GHSL 2000 and 2020 via `read_ghsl_built`; reproject pixel centres to lon/lat once, restrict to pixels inside the wanted cells, `mean_by_cell`, `growth_pp`), `nh_access` (`nh_access_km`), `rail_access`/`metro_access` (`station_access_km`), `road_strength` (`km_per_km2(arterial_km_by_cell)`), `name` (`name_cells` with `osm_places.parquet`), `bus_stops` (`bus_stop_counts`). Drop cells with `pop < min_area_population`. Save `data/processed/invest/cells.parquet` (cell, lat, lon, pop, the five raw factors, name, bus_stops) and the city↔cell membership table.
- [ ] **Step 3: score + `export` step.** For each cell and preset: sub-scores via `subscore`, `score_area`; mark `elig` (`pop ≥ best_area_min_population`, or all cells when fewer than 3 qualify). Per city and preset: `aggregate_city` over the city's cells with `pop` weights; `best_area` = top eligible cell by that preset's score; `factors` summary (population-weighted median raw value, `share` within `headline_band_km` for distance factors, city `subscore`); `data` block (`bus` from `bus_feeds_by_cell` when a feed has ≥ 50 stops inside the city's cells, `metro_stations`, `rail_stations` counts inside the city's cells). Write the fixtures exactly per spec §6 into `web/fixtures/invest/` (`meta.json` from config incl. the disclaimer text, `states.json` for all 36 with `city_count`, `cities.json` sorted by population desc, `areas/<id>.geojson.gz` with H3 polygons from `h3.cell_to_boundary` rounded to 4 decimals and features sorted by balanced score, `assets/<id>.json.gz` with stations, bus stops (GTFS cities only), highways (operational and under-construction NH lines clipped to the areas' bounding box + 5 km, simplified at 0.001°) and toll plazas from `osm_toll_plazas.parquet`). Round scores, sub-scores and raw values to 1 decimal; `null` for unobserved. The export is deterministic (sorted keys and rows, fixed gzip mtime = 0) and idempotent (writes to a temp directory, then swaps). It raises if a file exceeds 5 MB or the directory exceeds 25 MB.
- [ ] **Step 4: Tests** `ml/tests/test_invest_export.py`. The export's input contract is fixed here: `write_fixtures(out_dir: Path, cfg: ScoringConfig, cities: DataFrame, cells: DataFrame, memberships: DataFrame, assets: dict[str, dict], as_of: str) -> None`, where `cities` has `id, name, state (code), aliases (list), lat, lon, population, tier, geonameid`; `cells` has `cell, lat, lon, pop, name (str|None), bus_stops (float, NaN = no feed), nh_access, rail_access, metro_access, road_strength, built_up_growth` (raw values, NaN = unobserved); `memberships` has `city_id, cell`; `assets[city_id]` is `{"stations": [], "bus_stops": None | [], "bus_source": None | {...}, "highways": [], "toll_plazas": []}` (lists of GeoJSON-ready `(lon, lat, props)` tuples or line coordinate lists — the export turns them into FeatureCollections). `write_fixtures` computes sub-scores, scores, drivers, `elig`, city aggregates, `best_area`, provenance, and writes the tree. Tests:

```python
import gzip
import json

import h3
import numpy as np
import pandas as pd
import pytest

from pipeline.invest.export import write_fixtures
from pipeline.invest.scores import load_config


@pytest.fixture
def synthetic_world():
    cfg = load_config()
    ids = [h3.latlng_to_cell(18.50 + 0.03 * i, 73.80, 7) for i in range(5)]
    latlon = [h3.cell_to_latlng(c) for c in ids]
    cities = pd.DataFrame(
        [
            {"id": "alpha", "name": "Alpha", "state": "MH", "aliases": ["Alpha East"], "lat": 18.5, "lon": 73.8,
             "population": 300000.0, "tier": "mid", "geonameid": 1},
            {"id": "beta", "name": "Beta", "state": "MH", "aliases": [], "lat": 18.6, "lon": 73.9,
             "population": 200000.0, "tier": "mid", "geonameid": 2},
        ]
    )
    cells = pd.DataFrame(
        {
            "cell": ids,
            "lat": [p[0] for p in latlon],
            "lon": [p[1] for p in latlon],
            "pop": [9000.0, 6000.0, 1200.0, 8000.0, 5200.0],
            "name": ["Baner", None, "Pashan", "Wakad", "Aundh"],
            "bus_stops": [4.0, np.nan, np.nan, 2.0, 0.0],
            "nh_access": [1.0, 4.0, 30.0, 2.0, 9.0],
            "rail_access": [3.0, 8.0, 20.0, np.nan, 1.0],  # unobserved in one cell
            "metro_access": [40.0, 40.0, 40.0, 5.0, 0.5],
            "road_strength": [2.0, 1.0, 0.1, 1.5, 2.5],
            "built_up_growth": [30.0, 12.0, 2.0, 25.0, 6.0],
        }
    )
    memberships = pd.DataFrame(
        {"city_id": ["alpha"] * 3 + ["beta"] * 3, "cell": [ids[0], ids[1], ids[2], ids[2], ids[3], ids[4]]}
    )  # ids[2] belongs to both cities
    empty = {"stations": [], "bus_stops": None, "bus_source": None, "highways": [], "toll_plazas": []}
    return cfg, cities, cells, memberships, {"alpha": dict(empty), "beta": dict(empty)}


def test_export_is_valid_deterministic_and_provenanced(tmp_path, synthetic_world):
    cfg, cities, cells, memberships, assets = synthetic_world
    write_fixtures(tmp_path / "a", cfg, cities, cells, memberships, assets, "2026-09-29")
    write_fixtures(tmp_path / "b", cfg, cities, cells, memberships, assets, "2026-09-29")
    for f in sorted((tmp_path / "a").rglob("*")):
        if f.is_file():
            assert f.read_bytes() == (tmp_path / "b" / f.relative_to(tmp_path / "a")).read_bytes()
    city = json.loads((tmp_path / "a" / "cities.json").read_text())[0]
    for key in ("source", "source_ref", "fetched_at", "license", "confidence"):
        assert city[key] not in (None, "")
    area = json.loads(gzip.decompress(next((tmp_path / "a" / "areas").glob("*.gz")).read_bytes()))
    assert {"source", "fetched_at", "license"} <= set(area)
    for feat in area["features"]:
        p = feat["properties"]
        assert set(p["f"]) == set(p["s"]) == set(cfg.factors)
        for preset, weights in ((pid, pr.weights) for pid, pr in cfg.presets.items()):
            obs = {f: p["s"][f] for f in p["s"] if p["s"][f] is not None and weights[f] > 0}
            expected = sum(weights[f] * s for f, s in obs.items()) / sum(weights[f] for f in obs)
            assert abs(p["sc"][preset] - expected) <= 0.15  # the parity rule the Go store re-checks

def test_a_cell_shared_by_two_cities_has_identical_scores(tmp_path, synthetic_world):
    cfg, cities, cells, memberships, assets = synthetic_world
    write_fixtures(tmp_path, cfg, cities, cells, memberships, assets, "2026-09-29")

    def features(city):
        raw = gzip.decompress((tmp_path / "areas" / f"{city}.geojson.gz").read_bytes())
        return {f["properties"]["id"]: f["properties"] for f in json.loads(raw)["features"]}

    a, b = features("alpha"), features("beta")
    (cell,) = set(a) & set(b)
    assert a[cell]["sc"] == b[cell]["sc"] and a[cell]["s"] == b[cell]["s"]


def test_unobserved_factor_is_null_and_lowers_coverage_never_zero(tmp_path, synthetic_world):
    cfg, cities, cells, memberships, assets = synthetic_world
    write_fixtures(tmp_path, cfg, cities, cells, memberships, assets, "2026-09-29")
    raw = gzip.decompress((tmp_path / "areas" / "beta.geojson.gz").read_bytes())
    unobserved = [f["properties"] for f in json.loads(raw)["features"] if f["properties"]["f"]["rail_access"] is None]
    assert unobserved and all(p["s"]["rail_access"] is None and p["cov"] < 1 for p in unobserved)
```
  Add `test_invest_contract.py` — loads `api/testdata/invest/` (written by Track A) and `web/fixtures/invest/` and asserts identical key skeletons for `meta.json`, `states.json[0]`, `cities.json[0]` (incl. `scores.balanced`), the first area feature `properties` and the `assets` keys, with `null` matching any type (skips when either directory is missing):

```python
def compatible(a, b) -> bool:
    if a is None or b is None:
        return True
    if isinstance(a, dict) and isinstance(b, dict):
        return set(a) == set(b) and all(compatible(a[k], b[k]) for k in a)
    if isinstance(a, list) and isinstance(b, list):
        return not a or not b or compatible(a[0], b[0])
    num = (int, float)
    return (isinstance(a, num) and isinstance(b, num)) or type(a) is type(b)
```
  and `test_invest_spotchecks.py` (skips when the fixtures are absent): Maharashtra has ≥ 5 cities including ids `mumbai`, `pune`, `nagpur`, `nashik`; Pune's areas include ≥ 3 of {Hinjewadi, Kharadi, Hadapsar, Baner, Wakad, Wagholi}; a Haryana city has "Gurugram" as its name or alias; every state with `city_count` < 5 lists exactly that many cities; the banned-word rule from W6 is **not** here.
- [ ] **Step 5: Run the whole pipeline** `cd ml && uv run python -m pipeline.invest all`; fix what the spot checks reveal (name overrides go in `config/scoring.yaml` with a reason comment, after reading `review_pieces.csv`). Record the measured national percentiles of `road_strength` and `built_up_growth` in the config comments and adjust the knots only if the measured distribution makes them meaningless (say so in the commit).
- [ ] **Step 6: `sensitivity` step** — `uv run python -m pipeline.invest sensitivity` prints a Markdown table: per preset, the mean top-5 overlap per state (only states with ≥ 5 cities) under 200 random ±30 % weight perturbations (renormalised; seed 20260929), and the Spearman correlation between every pair of presets over all cities. Save the output to `data/processed/invest/sensitivity.md` (the lead pastes it into ADR-0015).
- [ ] **Step 7: Final checks and commit.** `cd ml && uv run pytest && uv run ruff check .` all green; `du -sh web/fixtures/invest` ≤ 25 MB. Commit in two steps: code + tests (`feat(invest): city and area scoring pipeline with fixture export`) and the generated fixtures (`data(invest): regenerate investor fixtures from 2026-09 sources`).

---

# Track A — Go API (`api/`)

Module `github.com/Punya23/INFRASTRUCTURE_AI/api`, Go stdlib only. Packages: `internal/store` (load and validate fixtures, in-memory indexes), `internal/http` with `package httpapi` (handlers and middleware), `cmd/api` (flags, wiring, graceful shutdown).

### The synthetic world (used by `api/testdata/invest/` and every test)

Never shipped and never served in production; every record has `"source": "synthetic-test"`. Presets = the four in spec §4 with the same weights. Sub-scores per city (order nh, rail, metro, roads, growth) — the city's `factors[f].subscore`; write each area's sub-scores so the city is their population-weighted mean (simplest: every area of a city has the city's sub-scores, differing only in `pop` and one tweaked factor for Pune's areas):

| id | state | tier | population | aliases | nh | rail | metro | roads | growth |
|---|---|---|---|---|---|---|---|---|---|
| mumbai | MH | metro | 12,600,000 | Thane, Navi Mumbai | 60 | 90 | 80 | 70 | 40 |
| pune | MH | metro | 6,100,000 | Pimpri-Chinchwad | 75 | 60 | 40 | 65 | 90 |
| nashik | MH | large | 1,900,000 | — | 85 | 40 | 0 | 45 | 70 |
| delhi | DL | metro | 22,000,000 | Noida | 70 | 80 | 90 | 85 | 45 |
| bengaluru | KA | metro | 11,000,000 | Bangalore | 65 | 45 | 60 | 60 | 80 |

States: MH, DL, KA, GA (`city_count` 0). Resulting scores (compute exactly, round to 1 decimal): **balanced** pune 70.5 › delhi 69.3 › bengaluru 65.0 › mumbai 63.0 › nashik 55.0; **commuter** delhi 73.8 › mumbai 69.5 › pune 63.5 › bengaluru 61.8 › nashik 40.5; **highway** pune 76.8 › nashik 70.3 › bengaluru 67.5 › delhi 66.0 › mumbai 57.5; **growth** pune 77.3 › bengaluru 70.3 › delhi 60.8 › nashik 59.8 › mumbai 55.0. Pune has 6 areas (one non-eligible, `pop` 1,200; one with `bus_stops` 31; one with `name: null`), Nashik 4, the rest 2. Pune has a bus feed (`PMPML`, secondary, 6,713 stops); the others `null`.

### Task 6 (A1): contract, store and testdata

**Files:**
- Create: `api/go.mod`, `api/openapi.yaml`, `api/internal/store/{types.go,store.go,store_test.go}`, `api/testdata/invest/**`

**Interfaces:**
- Produces: `store.Load(dir string) (*Store, error)`; `(*Store)` methods `Meta() Meta`, `States() []State`, `Cities() []City`, `City(id string) (*City, bool)`, `Areas(id string) (*AreaSet, bool)`, `Assets(id string) (*AssetSet, bool)`, `CitiesInState(code string) []*City`, `HasState(code string) bool`, `PresetIDs() []string`, `DefaultPreset() string`; types mirror spec §6 exactly (`Meta`, `Factor`, `Preset`, `City`, `PresetScore`, `FactorSummary`, `Driver`, `Provenance` embedded inline, `AreaSet`, `AreaFeature`, `AssetSet`).

- [ ] **Step 1: Write `api/openapi.yaml`** (OpenAPI 3.1) for every endpoint in spec §7 with parameter enums, the error schema and one full example per response built from the synthetic world (they double as frontend fixtures). Include `components/schemas` for `City`, `CityCard`, `AreaFeature` (properties as spec §7), `CompareResponse`, `Error`.
- [ ] **Step 2: `go mod init github.com/Punya23/INFRASTRUCTURE_AI/api`** (in `api/`).
- [ ] **Step 3: Author `api/testdata/invest/`** from the synthetic world: `meta.json`, `states.json`, `cities.json`, `areas/<id>.geojson`, `assets/<id>.json` (plain, not gzip) with hexagon-shaped polygons (any valid rings) and every field in spec §6. Compute all derived numbers (`sc`, `ac`, `d`, `g`, city `scores`, `best_area`, `cells`) with a throwaway script; do not commit the script.
- [ ] **Step 4: Write failing store tests** (`store_test.go`): `TestLoad_ok` (5 cities, 4 states, `CitiesInState("MH")` has 3, `Areas("pune")` has 6 features, `DefaultPreset() == "balanced"`); `TestLoad_failsClosed` table — missing directory, malformed `cities.json`, city whose `state` is not in `states.json`, city with no areas file, preset weights summing to 0.9, duplicate city id, invalid id (`Bad_ID`), area with a factor missing from `meta.factors` — each returns a non-nil error naming the offending file or field; `TestParity`: for every area feature and preset, `sc[preset]` equals the weighted mean of the non-null `s` values under `meta.presets[preset].weights` within 0.15, the sum of the top-3 driver points is ≤ `sc` + 0.15, and each city's `best_area.score` equals the highest `sc[preset]` among that city's `elig` features within 0.15. `Load` also accepts `areas/<id>.geojson.gz` and `assets/<id>.json.gz` (add `TestLoad_gzip`, writing a gzipped copy into `t.TempDir()`).
- [ ] **Step 5: Implement `store`.** `Load` reads `meta.json`, `states.json`, `cities.json`, then `areas/<id>.geojson[.gz]` and `assets/<id>.json[.gz]` for every city (gzip via `compress/gzip`), validates (rules above, id patterns from the Global Constraints, presets in `meta` cover every `scores` key, every factor id referenced exists), builds indexes (`map[string]*City`, `map[string][]*City` by state sorted by population descending, then id), and returns the first error wrapped with `%w` and the file path. Types use `*float64` for nullable numbers. `AreaFeature.Properties.D`/`G` decode from the fixture's `[["factor", number]]` pairs via a small `FactorPoint` type with `UnmarshalJSON`.
- [ ] **Step 6: Run** `go -C api vet ./... && go -C api test ./...` → pass. **Commit** `feat(api): OpenAPI contract, fixture store with fail-closed validation and synthetic test data`.

### Task 7 (A2): handlers and middleware

**Files:**
- Create: `api/internal/http/{server.go,handlers.go,compare.go,middleware.go,errors.go}`, tests `api/internal/http/{handlers_test.go,compare_test.go,middleware_test.go}`

**Interfaces:**
- Consumes: A1's `store`.
- Produces: `httpapi.Config{CORSOrigins []string; RatePerMinute int; RequestTimeout time.Duration; Now func() time.Time}` (`Now` nil = `time.Now`, injectable for the rate-limit window test); `httpapi.New(s *store.Store, cfg Config) http.Handler`; unexported middleware, each `func(http.Handler) http.Handler` so white-box tests can wrap a custom handler: `withRecover`, `withHeaders`, `withCORS(origins []string)`, `withRateLimit(perMinute int, now func() time.Time)`, `withTimeout(d time.Duration)`; unexported `compare(base *store.City, all []*store.City, preset, scope string, limit int) CompareResult`.

- [ ] **Step 1: Write the failing handler tests** (`handlers_test.go`, package `httpapi_test`; `newServer(t)` loads `../../testdata/invest` with `RatePerMinute: 1000`). Table-driven cases (each asserts status, `Content-Type: application/json`, and the fields named):

```go
func TestStateCities(t *testing.T) {
	h := newServer(t)
	cases := []struct {
		name, url string
		status    int
		ids       []string // expected order
		total     int
	}{
		{"balanced", "/v1/states/MH/cities?preset=balanced", 200, []string{"pune", "mumbai", "nashik"}, 3},
		{"commuter", "/v1/states/MH/cities?preset=commuter&limit=2", 200, []string{"mumbai", "pune"}, 3},
		{"highway", "/v1/states/MH/cities?preset=highway", 200, []string{"pune", "nashik", "mumbai"}, 3},
		{"default preset", "/v1/states/MH/cities", 200, []string{"pune", "mumbai", "nashik"}, 3},
		{"no cities", "/v1/states/GA/cities", 200, []string{}, 0}, // Review Focus 1: 200, not 404
		{"unknown state", "/v1/states/ZZ/cities", 404, nil, 0},
		{"lowercase code", "/v1/states/mh/cities", 400, nil, 0},
		{"bad preset", "/v1/states/MH/cities?preset=bogus", 400, nil, 0},
		{"limit 0", "/v1/states/MH/cities?limit=0", 400, nil, 0},
		{"limit 21", "/v1/states/MH/cities?limit=21", 400, nil, 0},
	}
	// for each: GET, check status; on 200 decode {total, cities[{rank,id}]}: ranks are 1..n in order
	// and equal `ids`; on errors the body is {"error":{"code","message"}} with code bad_request|not_found.
}
```
  Also: `TestSearch` (`q=pu` → first `pune`; `q=thane` → `mumbai` with `matched == "Thane"`; `q=Bang` → `bengaluru`; case-insensitive; prefix before substring); `TestSearch_badInput` (`q=p` → 400, 65-character `q` → 400, `q=%E0%A4%AA%E0%A5%81%E0%A4%A8%E0%A5%87` → 200, `q=<script>alert(1)</script>` → 200 with no match and the response never echoes the raw string unescaped, `q=../../etc/passwd` → 200 empty); `TestCity` (`/v1/cities/pune?preset=commuter` → `score` 63.5 ± 0.15, ≤ 3 drivers, `factors` has 5 keys, `data.bus.operator == "PMPML"`); `TestCity_badID` (`Pune` → 400, `../x` → 400, `nowhere` → 404); `TestAreas` (`/v1/cities/pune/areas?preset=balanced` → features sorted by `properties.score` descending, `rank` 1..6, `d[0]` has `factor`/`points`/`value`/`unit`, the `source`/`license`/`fetched_at` copied from the collection into every feature, `limit=2` → 2 features, `limit=1001` → 400); `TestAssets` (`layers=stations` → only `stations` and no `bus_stops` key; default → all four plus `bus_source`; `layers=bogus` → 400; a city without a feed → `bus_stops: null`); `TestMetaStatesHealth`.
- [ ] **Step 2: Write the failing compare tests** (`compare_test.go`) against the synthetic world:

```go
func TestCompare(t *testing.T) {
	h := newServer(t)
	rec := get(t, h, "/v1/cities/pune/compare?preset=commuter") // default scope for a metro = metros
	var got struct {
		Scope    string  `json:"scope"`
		Total    int     `json:"total"`
		BaseRank int     `json:"base_rank"`
		Others   []struct {
			ID     string  `json:"id"`
			Delta  float64 `json:"delta"`
			Better []struct{ Factor string; Delta, Base, Other float64 }
			Worse  []struct{ Factor string; Delta, Base, Other float64 }
		}
	}
	// decode → Scope "metros", Total 3, BaseRank 3 (delhi 73.8, mumbai 69.5, pune 63.5, bengaluru 61.8)
	// Others order: delhi (+10.3), mumbai (+6.0), bengaluru (-1.7)  — tolerance 0.11
	// delhi.Better = [metro_access +50 (40→90), rail_access +20]; delhi.Worse = [built_up_growth -45, nh_access -5]
	// ties on delta break by factor id ascending.
}
```
  plus: `scope=state` for Pune → `[mumbai, nashik]` ordered by score; `scope=india` → 4 others; `scope=peers` for Nashik (tier `large`, alone) → `others: []`, `total: 0`; Nashik's default scope is `peers`; `limit=11` → 400; `scope=galaxy` → 400; unknown city → 404; the base city never appears in `others`; `delta` = other − base for every row.
- [ ] **Step 3: Write the failing middleware tests** (`middleware_test.go`, **`package httpapi`** — white-box, wrapping a tiny stub handler with the unexported middleware; the endpoint-level ones may use `New`): CORS — an allowed `Origin` gets `Access-Control-Allow-Origin` echoed, a disallowed one gets none, `OPTIONS` preflight → 204 with `Allow-Methods: GET, OPTIONS` and no body; rate limit — `RatePerMinute: 2` → third request from the same `RemoteAddr` returns 429 with the JSON error and `Retry-After`, a different `RemoteAddr` is unaffected, the window resets after 60 s (inject a clock via `Config`-less unexported field or `time` func var); security headers — `X-Content-Type-Options: nosniff`, `Cache-Control: public, max-age=300` on `/v1/*`; panic recovery — a handler that panics yields 500 `internal` JSON with no stack in the body; timeout — a handler sleeping past `RequestTimeout` yields 503 JSON.
- [ ] **Step 4: Run to confirm failure. Step 5: Implement.** `server.go`: Go 1.22 mux patterns (`mux.HandleFunc("GET /v1/states/{code}/cities", …)`), middleware chain recover → security headers → CORS → rate limit → `http.TimeoutHandler` (JSON body). `errors.go`: `writeError(w, status, code, msg)`. `handlers.go`: parse helpers `parsePreset`, `parseLimit(min, max, default)` (out of range → error, never clamp), id/code validators with the two regexes, search normalisation (`strings.ToLower`, trim, collapse spaces; `q` 2–64 runes), ranking helper (score desc, population desc, id asc). `compare.go`: `compare(...)` per spec §7 (`delta` and per-factor differences rounded to 1 decimal with `math.Round(x*10)/10`; `better`/`worse` sorted by |delta| desc then factor id, at most 2 each; `base_rank` = 1 + count of candidates scoring higher). Rate limiter: fixed window per `RemoteAddr` host, map guarded by a mutex, map reset when it exceeds 10,000 keys. Never write `err.Error()` of internal errors to the client; log with `slog`.
- [ ] **Step 6: Run** `go -C api vet ./... && go -C api test ./... -race` → pass. **Commit** `feat(api): investor endpoints, compare logic, CORS, rate limit and timeouts`.

### Task 8 (A3): server binary, launch config, docs

**Files:**
- Create: `api/cmd/api/main.go`, `api/README.md`
- Modify: `.claude/launch.json`

- [ ] **Step 1: `main.go`.** Flags `-addr` (default `:8080`), `-data` (default `../web/fixtures/invest`); env `INVEST_CORS_ORIGINS` (comma list, default `http://localhost:8765`), `INVEST_RATE_LIMIT` (default 120). `store.Load` failure → log the error and `os.Exit(1)`. `http.Server{ReadHeaderTimeout: 5s, ReadTimeout: 10s, WriteTimeout: 15s, IdleTimeout: 60s}`; `signal.NotifyContext` for SIGINT/SIGTERM, `Shutdown` with a 10 s context. Log the loaded counts (`cities`, `areas`) and `as_of` with `slog`.
- [ ] **Step 2: Add to `.claude/launch.json`** a second configuration `{"name": "api", "runtimeExecutable": "go", "runtimeArgs": ["-C", "api", "run", "./cmd/api", "-addr", ":8080", "-data", "testdata/invest"], "port": 8080}` (switch `-data` to `../web/fixtures/invest` at integration).
- [ ] **Step 3: Smoke test.** Start with `preview_start` name `api`; `curl -s localhost:8080/healthz`, `/v1/states`, `/v1/states/MH/cities`, `/v1/cities/pune/compare?preset=commuter`; verify JSON, headers (`curl -si`) and that a corrupt data dir (copy testdata to a temp dir, truncate `cities.json`) makes the binary exit 1 with a clear message.
- [ ] **Step 4: `api/README.md`** — three commands (run, test, point at real fixtures), the endpoint table, the error format. **Commit** `feat(api): server binary with graceful shutdown, launch config and README`.

---

# Track W — web (`web/invest/`)

Design direction (spec §8): warm neutral canvas, teal and saffron from `web/index.html`, generous type, real data on the landing page, a hex/tile motif instead of an India outline, calm and credible rather than salesy. Load the `frontend-design:frontend-design` skill before writing CSS/markup. Pages are static HTML with ES modules; the language switcher comes from `../i18n.js` (`window.InfraI18n`, `t(key)` returns a string or `null`, no interpolation; dynamic text must re-render on the `infra-ai-lang-change` event). Node ≥ 22 runs unit tests with `node --test 'web/invest/js/*.test.mjs'`.

### Task 9 (W1): foundation — tokens, modules, i18n plumbing

**Files:**
- Create: `web/invest/invest.css`, `web/invest/js/{config,api,prefs,format,explain,ui}.js`, tests `web/invest/js/{api,prefs,format,explain}.test.mjs`
- Modify: `web/locales/en.json` (append `inv.*` keys as pages need them)

**Interfaces (exact — later tasks and tests rely on them):**
- `config.js`: `export const API_BASE`, `export const FETCH_TIMEOUT_MS = 8000`.
- `api.js`: `export class ApiError extends Error { status, code }`; `export async function getJson(path, { timeoutMs = FETCH_TIMEOUT_MS, fetchImpl = fetch, signal } = {})` (aborts its own `AbortController` at `timeoutMs` **and** races the fetch against a timer, so a fetch that ignores the signal still times out; rejects with `ApiError` — `code` `timeout`, `network`, `bad_response`, or the server's error code); `export const api = { meta(), states(), stateCities(code, {preset, limit}), searchCities(q, {limit}), city(id, {preset}), areas(id, {preset, limit}), assets(id, layers), compare(id, {preset, scope, limit}) }` each returning parsed JSON, building the query string with `URLSearchParams`.
- `prefs.js`: `export function loadPrefs(storage = globalThis.localStorage)` → `{ homeState: string|null, target: {type:'state',code}|{type:'city',id}|null, preset: string }` (values re-validated against `^[A-Z]{2}$`, `^[a-z0-9-]{2,64}$` and the four preset ids; anything else → defaults `{homeState:null,target:null,preset:'balanced'}`; every storage access in try/catch); `export function savePrefs(prefs, storage)` (never throws).
- `format.js`: `formatCount(n, lang)` (`en-IN`/`hi-IN`/`kn-IN` grouping: `61,00,000`), `formatScore(x)` (0 decimals, `"—"` for null/NaN), `formatDelta(x)` (`+7`, `−11`, `0`), `formatKm(x, lang)`, `formatValue(x, digits = 1)` (`"—"` for null/NaN/undefined — Review Focus 2), `tt(key, params, dict?)` (looks up `InfraI18n.t(key)` — or `dict[key]` in tests — falls back to the key itself, replaces `{name}` tokens from `params`, leaves unknown tokens untouched).
- `explain.js`: `export function explain(kind, item, meta)` with `kind` `'why'` or `'gap'`, returns `{ key, params }` (mapping below).
- `ui.js`: `h(tag, attrs, ...children)` (builds elements; string children become text nodes, never HTML; `attrs` `class`, `dataset`, `on*` handlers, ARIA), `clear(node)`, `renderSkeleton(node, rows)`, `renderError(node, message, onRetry)`, `onLangChange(cb)`, `setStatus(node, text)` (an `aria-live="polite"` region).

**explain mapping** (`prefix` = `inv.why` or `inv.gap`; `item` = `{factor, value, unit, share, band_km, …}`; `last(factor)` = the last knot value in `meta.factors[factor].bands`):
- `nh_access`, `rail_access`, `metro_access`: `share` and `band_km` present → `{prefix}.{factor}.share` with `{pct: Math.round(share*100), km: band_km}`; else `value == null` → `{prefix}.{factor}.unknown` `{}`; else `value > last(factor)` → `{prefix}.{factor}.far` `{km: last(factor)}`; else `{prefix}.{factor}.near` `{km: round1(value)}`.
- `road_strength`: `value == null` → `.unknown`; else `{prefix}.road_strength` `{km: round1(value)}`.
- `built_up_growth`: `value == null` → `.unknown`; else `{prefix}.built_up_growth` `{pp: Math.round(value)}`.

- [ ] **Step 1: Write failing tests.** `explain.test.mjs`:

```js
import test from 'node:test';
import assert from 'node:assert/strict';
import { explain } from './explain.js';

const meta = { factors: [
  { id: 'metro_access', bands: [[0,100],[1,90],[2,70],[5,30],[10,0]] },
  { id: 'nh_access', bands: [[0,100],[2,90],[5,70],[10,40],[25,0]] },
  { id: 'road_strength', bands: [[0,0],[3,100]] },
  { id: 'built_up_growth', bands: [[0,0],[40,100]] },
] };

test('share wins when the city summary has one', () => {
  assert.deepEqual(
    explain('why', { factor: 'metro_access', value: 3.1, unit: 'km', share: 0.22, band_km: 2 }, meta),
    { key: 'inv.why.metro_access.share', params: { pct: 22, km: 2 } });
});
test('beyond the last knot reads as far', () => {
  assert.deepEqual(explain('gap', { factor: 'metro_access', value: 40.2, unit: 'km', share: null, band_km: null }, meta),
    { key: 'inv.gap.metro_access.far', params: { km: 10 } });
});
test('near value is rounded to one decimal', () => {
  assert.deepEqual(explain('why', { factor: 'nh_access', value: 1.84, unit: 'km' }, meta),
    { key: 'inv.why.nh_access.near', params: { km: 1.8 } });
});
test('unobserved is unknown, never zero', () => {
  assert.equal(explain('why', { factor: 'road_strength', value: null }, meta).key, 'inv.why.road_strength.unknown');
  assert.equal(explain('why', { factor: 'built_up_growth', value: null }, meta).key, 'inv.why.built_up_growth.unknown');
});
test('growth and roads', () => {
  assert.deepEqual(explain('why', { factor: 'built_up_growth', value: 24.4 }, meta), { key: 'inv.why.built_up_growth', params: { pp: 24 } });
  assert.deepEqual(explain('why', { factor: 'road_strength', value: 2.24 }, meta), { key: 'inv.why.road_strength', params: { km: 2.2 } });
});
```

  `api.test.mjs` (inject `fetchImpl`): 200 → parsed JSON; 400 with `{"error":{"code":"bad_request","message":"…"}}` → rejects `ApiError` with `status 400`, `code 'bad_request'`; a fetch that never resolves → rejects `code 'timeout'` after `timeoutMs` (use 20 ms); a rejected fetch → `code 'network'`; a 200 with invalid JSON → `ApiError` `code 'bad_response'`; `api.stateCities('MH', {preset:'commuter', limit:3})` requests `/v1/states/MH/cities?preset=commuter&limit=3`; `api.searchCities('पुणे')` URL-encodes the query. `prefs.test.mjs`: round trip; a storage whose `getItem` throws → defaults; stored garbage (`homeState: '<x>'`, `preset: 'moon'`) → sanitised defaults; `savePrefs` with a throwing storage does not throw. `format.test.mjs`: `formatCount(6100000,'en') === '61,00,000'`; `formatScore(71.44) === '71'`; `formatScore(null) === '—'`; `formatDelta(7.4) === '+7'`, `formatDelta(-11.2) === '−11'`; `formatValue(undefined) === '—'`, `formatValue(NaN) === '—'`, `formatValue(0) === '0.0'` (an observed zero is not "unknown"); `tt('a {n} b', {n: 3}, {'a {n} b': 'x {n} y'}) === 'x 3 y'` and an unknown key returns the key.
- [ ] **Step 2: Run** `node --test 'web/invest/js/*.test.mjs'` → FAIL (modules missing). **Step 3: Implement the modules** to pass (pure, no DOM in `api/prefs/format/explain`). **Step 4: `invest.css`** — tokens mirroring `web/index.html` (`--canvas-base:#F7F6F2; --surface:#FFFFFF; --text-primary:#14202B; --text-secondary:#5B6773; --border-subtle:#E3E1DA; --brand-teal:#0E5A66; --accent-saffron:#E08A1E`), an 8 px spacing scale, type scale (Inter, Noto Sans Devanagari/Kannada via the existing font loading), components: button/CTA, chip, card, score ring (SVG-free `conic-gradient`), meter bar, skeleton shimmer (disabled under `prefers-reduced-motion`), error state, visually-hidden, focus-visible ring, layout containers with a 16 px gutter at 360 px. AA contrast on every text/background pair. **Step 5: Add the shared `inv.*` keys** (nav, footer, disclaimer, error, retry, loading, preset labels and one-line meanings, factor names, every `inv.why.*` and `inv.gap.*` key from the explain mapping — 5 factors × up to 4 variants × 2) to `web/locales/en.json`. **Step 6:** `node --test 'web/invest/js/*.test.mjs'` → pass. **Commit** `feat(web): investor foundation — API client, prefs, formatting, explanations, design tokens`.

### Task 10 (W2): landing page

**Files:** Create `web/invest/index.html`; Modify `web/index.html` (one nav link `<a class="nav-link text-title-md" href="invest/" data-i18n="inv.nav">Invest</a>` next to "Policymaker View"), `web/locales/en.json`.

- [ ] **Behaviour (all text via `data-i18n`/`tt`, English first):** header (brand, "Explore my area" link to `../index.html`, language switcher from `i18n.js`, primary CTA); hero — headline "Invest where infrastructure already delivers", sub-line naming the evidence (highways, metro and rail, roads, built-up growth), CTA "Find where to invest" → `start.html`, secondary "How it works" (anchor); a **live sample card** calling `api.stateCities('MH', {limit: 3})` showing rank, name, score and one why-chip per city, with skeleton while loading and an inline error with Retry (the page still reads well without it); "How it works" in three steps; "What we measure" (Access: highways, metro and rail, road network — Momentum: built-up growth — with the honest note "We measure road network capacity, not pavement condition"); "What this is not" (no forecasts, no price predictions, no financial advice); sources with licenses read from `api.meta()` (`sources[].name/license/attribution`); footer with the disclaimer line and OSM attribution. A CSS hex/tile grid motif (no India outline). Add a `<noscript>` line pointing to the static description.
- [ ] **Verify** (Browser pane or, if unavailable, report clearly): `preview_start` `web` and `api`; load `http://localhost:8765/invest/`; no console errors; sample card shows 3 MH cities from the API; CTA reaches `start.html`; 360 px and 1280 px screenshots; keyboard tab order reaches CTA and language switcher; stop the API → the card shows the error state with Retry and the rest of the page still renders (Review Focus 5). **Commit** `feat(web): investor landing page with live sample and nav link`.

### Task 11 (W3): start (onboarding)

**Files:** Create `web/invest/start.html`, `web/invest/js/start.js`; Modify `web/locales/en.json`.

- [ ] **Behaviour:** a three-step wizard on one page with a progress indicator and Back/Next/Skip, focus moved to each step's heading, `aria-live` status. **Step 1** "Which state do you belong to?" — searchable grid of all 36 states/UTs from `api.states()`, each tile showing the name and "N cities" (0 → "No city above 1 lakh people yet"), plus "Skip". **Step 2** "Where are you planning to invest?" — three big choices: "In {home state}" (hidden if step 1 was skipped), "Another state" (reveals the same grid), "A specific city" (search input with 250 ms debounce → `api.searchCities`, results show name, state and tier; keyboard operable listbox; no match → "No city found. Try a state instead."). **Step 3** "What matters most?" — four preset chips (balanced default, commuter, highway, growth) with one-line meanings, then "Show me". On finish `savePrefs` and navigate: a state → `state.html?s=<CODE>&preset=<id>`, a city → `city.html?c=<id>&preset=<id>`. If saved prefs exist, pre-fill and show "Continue where you left off". No personal data is asked or stored.
- [ ] **Verify:** walk the wizard with the keyboard only and with the mouse; pick Maharashtra → Maharashtra → Balanced → lands on `state.html?s=MH&preset=balanced`; search "thane" → Mumbai (alias) selectable; search `<script>alert(1)</script>` → "No city found" and no script runs (Review Focus 4); Back keeps answers; reload restores prefs; storage disabled (`localStorage` throwing) still works. **Commit** `feat(web): three-step investor onboarding`.

### Task 12 (W4): state result

**Files:** Create `web/invest/state.html`, `web/invest/js/state.js`; Modify `web/locales/en.json`.

- [ ] **Behaviour:** reads `s` and `preset` from the URL (invalid → redirect to `start.html`); fetches `api.stateCities(code, {preset, limit: 5})` and `api.states()` for the name; preset chips re-fetch and update the URL with `history.replaceState`. Each card: rank, city name with state, tier badge, score ring (`formatScore`), Access and Momentum meters, up to three why-chips from `explain('why', driver, meta)`, one watch-out from `explain('gap', gap, meta)` (hidden when none), best-area line ("Best area: {name}" or "Area near …" when the name is null), coverage note when `coverage < 1` ("Based on N of M factors"), and "Explore {city}" → `city.html?c=<id>&preset=<preset>`. **Fewer than five:** "Only {n} cities above 1 lakh people in {state}" (n ≥ 1); **none:** an empty state with a link to pick another state (Review Focus 1). Aside "Other metros to compare": top 3 from `api.compare(topCityId, {preset, limit: 3})` (skipped when the state has no city). Persistent disclaimer line. Loading skeletons, error state with Retry.
- [ ] **Verify:** MH → 3 cards on the synthetic data (5 on real data) in the correct order per preset; `?s=GA` → empty state; `?s=ZZ` → friendly not-found with a link back; switching preset reorders; 360 px layout stacks aside below cards; stop the API → error state, Retry recovers after restart. **Commit** `feat(web): state result page with top cities, reasons and metro comparison`.

### Task 13 (W5): city page

**Files:** Create `web/invest/city.html`, `web/invest/js/city.js`, `web/invest/js/map.js`; Modify `web/locales/en.json`.

- [ ] **Behaviour:** reads `c` and `preset`; fetches `api.city`, `api.areas(id, {preset, limit: 1000})`, `api.compare(id, {preset})` in parallel (each with its own skeleton and error/retry). **Header:** name, state, tier, population (`formatCount`), built-up growth, data flags ("Bus data: {operator}" or "No bus feed for this city — bus stops are shown only where a feed exists and are not scored"), preset chips. **Map** (`map.js`, MapLibre GL 4.7.1 from unpkg as in `nh-explorer.html`): OpenFreeMap positron style (`https://tiles.openfreemap.org/styles/positron`), falling back to a plain background style if the style request errors; the `areas` GeoJSON as a fill layer coloured by `score` on a 5-step sequential teal ramp with a legend, thin outline, non-eligible cells at reduced opacity; click and hover popups (name, score, top drivers, gaps, bus stops, "Area near …" when unnamed) built with DOM APIs; `fitBounds` to the areas; layer toggles (stations by mode, bus stops, highways by status, tolls) that lazy-load `api.assets(id, layers)` once and show/hide; attribution "© OpenStreetMap contributors" always visible. **Best areas list:** top 10 features with `elig`, best cell per name, rank/name/score/why-chips, a `<button>` per row that flies the map to the cell and opens its popup — the keyboard and screen-reader path. **Compare panel** (right column; stacked under the map below 900 px): scope switch (Metros / Similar-size / This state / All India) re-calling `api.compare`; rows with name, score, `formatDelta(delta)` chip (green above, neutral below), and reasons "{Better factor} +50 · {Worse factor} −45" from `better`/`worse`; each row links to `city.html?c=<id>&preset=<preset>`; text "You are here: rank {base_rank} of {total + 1}"; when `others` is empty: "No comparable cities for this filter." Disclaimer line and methodology note ("Growth favours the fringe, access favours the core") in a collapsible "How to read this".
- [ ] **Verify** (Browser pane): `city.html?c=pune&preset=commuter` — map draws hexes, popup works, layers toggle, list button focuses the map cell, compare shows Delhi first with the "+50 metro access" reason (synthetic data) and clicking it opens Delhi with the same preset; unnamed cell shows "Area near …"; `?c=zzz` → not-found state; API stopped → each section shows an error with Retry while the others stay; keyboard-only path; 360 px layout; console clean. **Commit** `feat(web): city page with hex heat map, best areas, layers and compare panel`.

### Task 14 (W6): languages, guards, polish

**Files:** Modify `web/locales/{en,hi,kn}.json`; Create `ml/tests/test_invest_copy.py` (this single test lives in `ml/tests/` so `uv run pytest` guards it — allowed exception to the track boundary).

- [ ] **Step 1:** Add Hindi and Kannada translations for every `inv.*` key (natural, not literal; keep numbers and `{tokens}` intact; note in the commit that they need native-speaker review). Other locales fall back to English. Run `node web/validate-translations.js` and confirm no *English* key is missing and that the only `inv.*` gaps are in the fallback locales.
- [ ] **Step 2: Write `ml/tests/test_invest_copy.py`:**

```python
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BANNED = re.compile(r"\b(returns?|roi|yields?|profit(s|able)?|appreciation|guaranteed)\b", re.I)
STRING_LITERAL = re.compile(r"\"([^\"\n]{3,})\"|'([^'\n]{3,})'|`([^`]{3,})`")


def _visible_text():
    """Text a visitor can read: HTML text nodes, JS string literals, and inv.* locale values.
    JS code itself is skipped, so the `return` keyword is not mistaken for the word."""
    for path in sorted((ROOT / "web" / "invest").rglob("*")):
        if path.suffix == ".html":
            yield path.name, re.sub(r"<[^>]+>", " ", path.read_text(encoding="utf-8"))
        elif path.suffix in {".js", ".mjs"} and not path.name.endswith(".test.mjs"):
            for m in STRING_LITERAL.finditer(path.read_text(encoding="utf-8")):
                yield path.name, next(g for g in m.groups() if g)
    for lang in ("en", "hi", "kn"):
        data = json.loads((ROOT / "web" / "locales" / f"{lang}.json").read_text(encoding="utf-8"))
        for key, value in data.items():
            if key.startswith("inv."):
                yield f"{lang}:{key}", value


def test_guard_catches_what_it_should():
    assert BANNED.search("Expected returns of 12% a year")
    assert BANNED.search("Guaranteed ROI")
    assert not BANNED.search("Access and momentum scores")


def test_no_returns_or_forecast_language():
    hits = [(name, m.group(0)) for name, text in _visible_text() for m in BANNED.finditer(text)]
    assert not hits, hits


def test_pages_use_no_inline_script_and_no_inner_html():
    for path in (ROOT / "web" / "invest").rglob("*.html"):
        text = path.read_text(encoding="utf-8")
        assert not re.search(r"<script(?![^>]*\bsrc=)", text), f"{path.name}: inline script"
        assert not re.search(r"\son[a-z]+=", text), f"{path.name}: inline event handler"
    for path in (ROOT / "web" / "invest").rglob("*.js"):
        text = path.read_text(encoding="utf-8")
        assert "innerHTML" not in text and "insertAdjacentHTML" not in text, path.name
```
- [ ] **Step 3: Polish pass:** WCAG AA contrast check on every text/background pair (compute ratios with a small script), visible focus everywhere, `prefers-reduced-motion`, no horizontal scroll at 360 px on all four pages, `lang` attribute and font switch when the language changes (Hindi and Kannada render with Noto), numbers use Indian grouping in `en`/`hi`/`kn`, page titles and meta descriptions, favicon reuse from `web/`. Take 1280 px and 360 px screenshots of all four pages (English and Hindi for the city page) and save them under `docs/superpowers/plans/screenshots/` only if the lead asks — otherwise attach in the report.
- [ ] **Step 4:** `uv run --project ml pytest ml/tests/test_invest_copy.py -q` and `node --test 'web/invest/js/*.test.mjs'` pass. **Commit** `feat(web): Hindi and Kannada strings and copy guards for the investor flow`.

---

# Integration (lead)

### Task 15 (I1): real-data integration

- [ ] Point the API at the real fixtures (`-data ../web/fixtures/invest` in `.claude/launch.json`); start `api` and `web`; run `ml/tests/test_invest_contract.py` (golden vs real skeleton) and `test_invest_spotchecks.py`; walk the whole flow in the browser on real Maharashtra, Delhi and Haryana data; fix name overrides, copy and layout issues found; confirm the API loads in under 3 s and every `/v1/*` route answers under 100 ms locally.
- [ ] Review the pipeline output like a sceptical user: is any top-5 list embarrassing (a village, a duplicate metro region, a wrong state)? Fix at the source (config, override, threshold) — never patch the fixtures by hand.

### Task 16 (I2): ADR, README, AGENTS, methodology

- [ ] Write `docs/adr/0015-investor-onboarding-scores-and-api.md` (Status Proposed): the decisions of spec §2, the score definition, "Go API before Postgres", the no-returns stance, the sensitivity table from `data/processed/invest/sensitivity.md`; add its row to `docs/adr/README.md`.
- [ ] README §9 (product surface 6: investor flow), §10 (the new endpoints), §12 (`web/invest/`, `api/`, `config/scoring.yaml`, `config/states.yaml`, `ml/pipeline/invest/`), §13 status; AGENTS.md: Status line, Commands (`cd ml && uv run python -m pipeline.invest all`, `go -C api run ./cmd/api`, `node --test 'web/invest/js/*.test.mjs'`); note in `docs/fields/README.md` that fixtures under `web/fixtures/invest/` are cross-field.

### Task 17 (I3): whole-branch review and fixes

- [ ] Run `/code-review` style review on the diff against `main` (correctness → robustness → security → contracts → dead weight → tests), verify each finding against the code, fix, rerun `cd ml && uv run pytest && uv run ruff check .`, `go -C api vet ./... && go -C api test ./... -race`, `node --test 'web/invest/js/*.test.mjs'`.

### Task 18 (I4): merge and push

- [ ] `git fetch origin`; merge `origin/main` into the branch (resolve conflicts for real; regenerate fixtures if they conflict); rerun all checks; fast-forward merge into `main` and `git push origin main` (push as Punya23; no PR — standing user rule); delete the merged remote branch except the checked-out worktree branch, and say so.

## Self-review (done while writing)

- **Spec coverage:** flow §1 → W2–W5; decisions §2 → Global Constraints, I2; architecture §3 → track split; scoring §4 → D1, D4, D5; cities/areas §5 → D2, D3, D5; fixtures §6 → D5, A1; API §7 → A1–A3; web §8 → W1–W6; invariants §9 → Global Constraints and tests; testing §10 → per-task tests plus I1; risks §11 → D5 review files, I1.
- **Types consistent across tracks:** factor ids, preset ids, `sc/ac/d/g/s/f/elig` keys and provenance names are identical in D5's export, A1's Go types, the synthetic world and W's `explain`; the contract test (D5) locks the Python/Go/JSON skeletons together.
- **No placeholders:** the only deliberately unspecified choices are algorithm details inside functions whose tests pin the behaviour (NH sampling step, popup styling); the config knots are initial values verified in D5 step 5.
