"""Spot checks on the real fixtures (spec §10); skipped until the pipeline has written them."""

import gzip
import json
import re
from collections import Counter

import pytest

from pipeline.invest.scores import ROOT

FIXTURES = ROOT / "web" / "fixtures" / "invest"
pytestmark = pytest.mark.skipif(
    not (FIXTURES / "cities.json").exists(), reason="run: python -m pipeline.invest all"
)
# OSM spells Pune's IT hub "Hinjawadi"; an area name counts when a spelling is a word of it
# ("Wakad gaav", "Hinjawadi Phase 1")
PUNE_LOCALITIES = {
    "Hinjewadi": ("Hinjewadi", "Hinjawadi"),
    "Kharadi": ("Kharadi",),
    "Hadapsar": ("Hadapsar",),
    "Baner": ("Baner",),
    "Wakad": ("Wakad",),
    "Wagholi": ("Wagholi",),
}


@pytest.fixture(scope="module")
def cities():
    return json.loads((FIXTURES / "cities.json").read_text())


def test_maharashtra_has_its_four_biggest_cities(cities):
    ids = {c["id"] for c in cities if c["state"] == "MH"}
    assert len(ids) >= 5 and {"mumbai", "pune", "nagpur", "nashik"} <= ids


def test_pune_areas_include_three_known_localities():
    raw = gzip.decompress((FIXTURES / "areas" / "pune.geojson.gz").read_bytes())
    names = [f["properties"]["name"] for f in json.loads(raw)["features"]]
    found = {
        place
        for place, spellings in PUNE_LOCALITIES.items()
        if any(re.search(rf"\b{s}\b", n, re.IGNORECASE) for s in spellings for n in names if n)
    }
    assert len(found) >= 3, f"only {sorted(found)}"


def test_a_haryana_city_is_found_as_gurugram(cities):
    assert any(c["state"] == "HR" and "Gurugram" in [c["name"], *c["aliases"]] for c in cities)


def test_every_small_state_lists_exactly_its_cities(cities):
    per_state = Counter(c["state"] for c in cities)
    states = json.loads((FIXTURES / "states.json").read_text())
    assert len(states) == 36
    for s in states:
        if s["city_count"] < 5:
            assert per_state[s["code"]] == s["city_count"], s["code"]
    assert any(s["city_count"] == 0 for s in states)  # the API must answer total 0 somewhere
