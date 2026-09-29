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


def test_gaps_rank_by_weighted_shortfall_not_raw_subscore(cfg):
    # nh (weight 0.25) at 30 leaves 17.5 points on the table; rail (0.15) at 5 leaves 14.25
    r = score_area(cfg, "balanced", {**ALL_80, "nh_access": 30.0, "rail_access": 5.0})
    assert [f for f, _ in r.gaps] == ["nh_access", "rail_access"]


def test_zero_weight_factor_is_never_a_watch_out(cfg):
    r = score_area(cfg, "highway", {**ALL_80, "metro_access": 0.0})  # the highway preset ignores metro
    assert r.score == pytest.approx(80.0)
    assert r.gaps == ()


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


def test_city_coverage_confidence_access_momentum_are_population_weighted(cfg):
    a = score_area(cfg, "balanced", {**ALL_80, "metro_access": None})  # coverage 0.85, momentum 80
    b = score_area(cfg, "balanced", {**ALL_80, "nh_access": 20.0, "built_up_growth": 20.0})
    c = aggregate_city(cfg, "balanced", [a, b], [3000, 1000])
    assert c.coverage == pytest.approx((0.85 * 3 + 1.0) / 4)
    assert c.confidence == pytest.approx(0.8 * c.coverage)
    assert c.momentum == pytest.approx((80 * 3 + 20) / 4)
    assert c.access == pytest.approx((a.access * 3 + b.access) / 4)


def test_city_rejects_empty_and_zero_population(cfg):
    a = score_area(cfg, "balanced", ALL_80)
    with pytest.raises(ValueError):
        aggregate_city(cfg, "balanced", [], [])
    with pytest.raises(ValueError):
        aggregate_city(cfg, "balanced", [a], [0])
