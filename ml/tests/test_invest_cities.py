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


def test_unnamed_piece_beside_a_named_one_keeps_none_and_integer_ids():
    pieces = pd.DataFrame({"label": [1, 2], "population": [900_000, 120_000]})
    places = pd.DataFrame(
        {
            "geonameid": [10],
            "name": ["Faridabad"],
            "lat": [28.40],
            "lon": [77.31],
            "population": [1_400_000],
            "label": [1],
        }
    )
    out = name_pieces(pieces, places, overrides={})
    assert out.loc[1, "name"] is None  # not NaN: callers test for None
    assert str(out.loc[0, "geonameid"]) == "10"  # not "10.0": it becomes a source_ref
    assert out.loc[1, ["geonameid", "lat", "lon"]].isna().all()


def test_make_slugs_disambiguates_by_state_then_counter():
    names = ["Aurangabad", "Aurangabad", "Pune", "Pune", "Nashik"]
    states = ["MH", "BR", "MH", "MH", "MH"]
    assert make_slugs(names, states) == ["aurangabad-mh", "aurangabad-br", "pune-mh", "pune-mh-2", "nashik"]


def test_make_slugs_are_ascii_and_api_safe():
    (slug,) = make_slugs(["São  Paulo!"], ["MH"])
    assert slug == "sao-paulo"


def test_make_slugs_rejects_mismatched_lengths():
    with pytest.raises(ValueError):  # zip would silently drop a city
        make_slugs(["Pune", "Nashik"], ["MH"])


@pytest.mark.parametrize(
    ("population", "tier"), [(2_500_000, "metro"), (2_499_999, "large"), (1_000_000, "large"), (999_999, "mid")]
)
def test_tier_of(population, tier):
    assert tier_of(population, 2_500_000, 1_000_000) == tier
