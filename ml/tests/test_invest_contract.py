"""The pipeline's fixtures and the Go API's golden test data share one skeleton (spec §6).

api/testdata/invest (Track A) is what the Go store is tested against; web/fixtures/invest is what
the pipeline writes. Skips while either directory is missing.
"""

import gzip
import json

import pytest

from pipeline.invest.scores import ROOT

GOLDEN = ROOT / "api" / "testdata" / "invest"
FIXTURES = ROOT / "web" / "fixtures" / "invest"


def compatible(a, b) -> bool:
    if a is None or b is None:
        return True
    if isinstance(a, dict) and isinstance(b, dict):
        return set(a) == set(b) and all(compatible(a[k], b[k]) for k in a)
    if isinstance(a, list) and isinstance(b, list):
        return not a or not b or compatible(a[0], b[0])
    num = (int, float)
    return (isinstance(a, num) and isinstance(b, num)) or type(a) is type(b)


def _load(path):
    data = path.read_bytes()
    return json.loads(gzip.decompress(data) if path.suffix == ".gz" else data)


def _skeleton(root):
    area = _load(min((root / "areas").iterdir()))
    return {
        "meta.json": _load(root / "meta.json"),
        "states.json[0]": _load(root / "states.json")[0],
        "cities.json[0]": _load(root / "cities.json")[0],
        "first area feature properties": area["features"][0]["properties"],
        "assets keys": dict.fromkeys(_load(min((root / "assets").iterdir()))),
    }


@pytest.mark.skipif(
    not (GOLDEN / "meta.json").exists() or not (FIXTURES / "meta.json").exists(),
    reason="needs api/testdata/invest and web/fixtures/invest",
)
@pytest.mark.parametrize(
    "part",
    ["meta.json", "states.json[0]", "cities.json[0]", "first area feature properties", "assets keys"],
)
def test_fixtures_match_the_go_golden_skeleton(part):
    golden, ours = _skeleton(GOLDEN)[part], _skeleton(FIXTURES)[part]
    assert compatible(golden, ours), f"{part}: golden {golden!r} vs fixtures {ours!r}"


def test_compatible_matches_null_to_any_type_and_nothing_else():
    assert compatible({"a": None, "b": [1]}, {"a": "x", "b": [2.5]})
    assert not compatible({"a": 1}, {"a": 1, "b": 2})  # an extra key is a contract break
    assert not compatible({"a": "1"}, {"a": 1})
