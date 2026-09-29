import re

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


def test_nan_density_is_background_even_at_a_zero_threshold():
    density = np.array([[np.nan, 0.0, 10.0]])
    labels, _ = label_urban_centres(density, np.ones((1, 3), int), 0)
    assert labels.tolist() == [[0, 1, 1]]


@pytest.mark.parametrize("density", [[[2000.0, 0.0, 2000.0]], [[2000.0], [0.0], [2000.0]]])
def test_cells_on_opposite_edges_of_the_grid_are_not_connected(density):
    density = np.array(density)
    labels, _ = label_urban_centres(density, np.ones(density.shape, int), 1500)
    assert labels.max() == 2  # a negative index must not wrap one edge onto the other


def test_shape_mismatch_is_rejected():
    with pytest.raises(ValueError, match="same shape"):
        label_urban_centres(np.zeros((2, 2)), np.zeros((2, 3), int), 1500)


def test_connectivity_other_than_4_or_8_is_rejected():
    with pytest.raises(ValueError, match="4 or 8"):
        label_urban_centres(np.zeros((2, 2)), np.zeros((2, 2), int), 1500, connectivity=6)


def test_a_blob_outside_every_state_polygon_is_state_0_for_review():
    labels, label_state = label_urban_centres(np.full((2, 2), 2000.0), np.zeros((2, 2), int), 1500)
    assert labels.max() == 1 and label_state == {1: 0}


def test_an_unknown_cell_borrows_only_from_urban_neighbours():
    density = np.array([[0, 0, 0], [2000, 2000, 0]], dtype=float)
    # the state-0 urban cell (1,1) touches state-2 land above it that is not urban, and an urban
    # cell of state 1 on its left: only the urban neighbour counts
    state = np.array([[0, 2, 0], [1, 0, 0]])
    labels, label_state = label_urban_centres(density, state, 1500)
    assert labels[1, 0] == labels[1, 1] and label_state == {1: 1}


def test_an_unknown_cell_between_urban_neighbours_of_two_states_stays_unknown():
    labels, label_state = label_urban_centres(np.full((1, 3), 2000.0), np.array([[1, 0, 2]]), 1500)
    assert sorted(label_state.values()) == [0, 1, 2] and len(set(labels[0])) == 3


def test_state_borrowing_reaches_three_cells_and_no_further():
    density = np.zeros((1, 9))
    density[0, 1:8] = 2000
    state = np.zeros((1, 9), dtype=int)
    state[0, 1:4] = 7  # cells 4-7 fall outside every polygon
    labels, label_state = label_urban_centres(density, state, 1500)
    assert labels[0, 1] == labels[0, 6] != labels[0, 7]  # three rounds reach cell 6, not cell 7
    assert sorted(label_state.values()) == [0, 7]


# A 2x2 grid of 0.1-degree cells: pixel (0,0) spans lon 73.0-73.1, lat 18.9-19.0.
GRID = Affine(0.1, 0, 73.0, 0, -0.1, 19.0)


@pytest.mark.filterwarnings("error")  # affine deprecates `transform * point`; a warning must fail
def test_assign_places_uses_the_raster_cell():
    labels = np.zeros((2, 2), dtype=np.int32)
    labels[0, 0] = 5
    places = pd.DataFrame({"lon": [73.05, 73.15, 80.0], "lat": [18.95, 18.95, 18.95]})
    assert assign_places(places, labels, GRID)["label"].tolist() == [5, 0, 0]


@pytest.mark.filterwarnings("error")
def test_assign_places_off_the_grid_on_any_side_is_outside():
    labels = np.array([[1, 2], [3, 4]], dtype=np.int32)  # no empty cell, so a wrap-around shows
    places = pd.DataFrame(
        {
            # inside, inside, west of the grid, north, east, south
            "lon": [73.05, 73.15, 72.95, 73.05, 73.25, 73.05],
            "lat": [18.95, 18.85, 18.95, 19.05, 18.95, 18.75],
        }
    )
    assert assign_places(places, labels, GRID)["label"].tolist() == [1, 4, 0, 0, 0, 0]


@pytest.mark.filterwarnings("error")
def test_assign_places_non_finite_coordinates_are_outside_without_a_warning():
    labels = np.full((2, 2), 9, dtype=np.int32)
    places = pd.DataFrame(
        {"lon": [np.nan, 73.05, np.inf, 73.05], "lat": [18.95, np.nan, 18.95, -np.inf]}
    )
    assert assign_places(places, labels, GRID)["label"].tolist() == [0, 0, 0, 0]


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
    out = name_pieces(pieces, places, overrides={}, big_place=100_000).set_index("label")
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
    out = name_pieces(pieces, places, overrides={11: "Gurugram"}, big_place=100_000).iloc[0]
    assert out["name"] == "Gurugram" and out["aliases"] == ["Faridabad"]
    assert (out["lat"], out["lon"]) == (28.46, 77.03)


def test_piece_without_a_place_gets_no_name():
    out = name_pieces(
        pd.DataFrame({"label": [3], "population": [120_000]}),
        pd.DataFrame(
            {"geonameid": [], "name": [], "lat": [], "lon": [], "population": [], "label": []}
        ),
        overrides={},
        big_place=100_000,
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
    out = name_pieces(pieces, places, overrides={}, big_place=100_000)
    assert out.loc[1, "name"] is None  # not NaN: callers test for None
    assert str(out.loc[0, "geonameid"]) == "10"  # not "10.0": it becomes a source_ref
    assert out.loc[1, ["geonameid", "lat", "lon"]].isna().all()


def _one_piece():
    return pd.DataFrame({"label": [1], "population": [900_000]})


def _places(rows, label=1):
    """GeoNames places in one piece; rows are (geonameid, name, population)."""
    ids, names, populations = zip(*rows)
    return pd.DataFrame(
        {
            "geonameid": ids,
            "name": names,
            "lat": 28.0,
            "lon": 77.0,
            "population": populations,
            "label": label,
        }
    )


def test_big_place_is_required_because_it_is_config():
    with pytest.raises(TypeError, match="big_place"):
        name_pieces(_one_piece(), _places([(1, "A", 5)]), overrides={})


def test_a_single_big_place_needs_no_review():
    places = _places([(1, "Kota", 400_000), (2, "Sakatpura", 99_999)])
    out = name_pieces(_one_piece(), places, {}, big_place=100_000).iloc[0]
    assert out["name"] == "Kota" and out["aliases"] == [] and bool(out["review"]) is False


def test_a_place_of_exactly_big_place_people_counts_and_one_fewer_does_not():
    places = _places([(1, "Kota", 400_000), (2, "Exactly", 100_000), (3, "One short", 99_999)])
    out = name_pieces(_one_piece(), places, {}, big_place=100_000).iloc[0]
    assert out["aliases"] == ["Exactly"] and bool(out["review"]) is True


def test_equal_populations_go_to_the_lower_geonameid():
    places = _places([(21, "Twenty-one", 200_000), (20, "Twenty", 200_000)])  # higher id first
    out = name_pieces(_one_piece(), places, {}, big_place=100_000).iloc[0]
    assert (out["name"], out["geonameid"], out["aliases"]) == ("Twenty", 20, ["Twenty-one"])


def test_empty_pieces_give_empty_naming_columns():
    empty = pd.DataFrame({"label": [], "population": []})
    out = name_pieces(empty, _places([(1, "A", 5)]), {}, big_place=100_000)
    assert out.empty and {"name", "geonameid", "lat", "lon", "aliases", "review"} <= set(
        out.columns
    )


def test_renaming_the_anchor_keeps_its_geonames_name_as_an_alias():
    places = _places([(10, "Faridabad", 1_400_000), (11, "Gurgaon", 876_000)])
    out = name_pieces(_one_piece(), places, {11: "Gurugram"}, big_place=100_000).iloc[0]
    assert out["name"] == "Gurugram" and out["aliases"] == ["Gurgaon", "Faridabad"]


def test_two_overrides_in_one_piece_the_larger_place_wins_and_the_other_is_an_alias():
    places = _places(
        [(10, "Mumbai", 12_000_000), (11, "Navi Mumbai", 1_100_000), (12, "Thane", 1_800_000)]
    )
    # dict order and geonameid order both favour 11; the larger place (12) must still win
    overrides = {11: "Navi Mumbai City", 12: "Thane"}
    out = name_pieces(_one_piece(), places, overrides, big_place=100_000).iloc[0]
    assert (out["name"], out["geonameid"]) == ("Thane", 12)
    # largest first; the losing override's place is listed under its override name
    assert out["aliases"] == ["Mumbai", "Navi Mumbai City"]


def test_an_override_on_a_small_place_still_lists_it_as_an_alias():
    places = _places([(1, "Kota", 400_000), (2, "Sakatpura", 50_000)])
    out = name_pieces(_one_piece(), places, {1: "Kota", 2: "Sakat"}, big_place=100_000).iloc[0]
    assert out["aliases"] == ["Sakat"] and bool(out["review"]) is False  # review counts big places


@pytest.mark.parametrize(
    ("overrides", "listed"),
    [
        ({999: "Nowhere"}, "[999]"),  # no such place
        ({12: "Rural"}, "[12]"),  # a place that lies outside every piece
        ({999: "Nowhere", 12: "Rural", 10: "Faridabad"}, "[12, 999]"),  # every stale id, sorted
    ],
)
def test_a_stale_override_raises_and_names_its_ids(overrides, listed):
    places = pd.concat(
        [_places([(10, "Faridabad", 1_400_000)]), _places([(12, "Rural", 5_000)], label=0)],
        ignore_index=True,
    )
    with pytest.raises(ValueError, match=re.escape(f"lie in no piece: {listed}")):
        name_pieces(_one_piece(), places, overrides, big_place=100_000)


def test_make_slugs_disambiguates_by_state_then_counter():
    names = ["Aurangabad", "Aurangabad", "Pune", "Pune", "Nashik"]
    states = ["MH", "BR", "MH", "MH", "MH"]
    assert make_slugs(names, states) == [
        "aurangabad-mh",
        "aurangabad-br",
        "pune-mh",
        "pune-mh-2",
        "nashik",
    ]


def test_make_slugs_are_ascii_and_api_safe():
    (slug,) = make_slugs(["São  Paulo!"], ["MH"])
    assert slug == "sao-paulo"


def test_make_slugs_numbers_three_same_state_duplicates():
    assert make_slugs(["Pune"] * 3, ["MH"] * 3) == ["pune-mh", "pune-mh-2", "pune-mh-3"]


def test_make_slugs_rejects_a_name_that_slugifies_to_an_existing_suffixed_id():
    with pytest.raises(ValueError, match=re.escape("duplicate city ids: ['pune-mh-2']")):
        make_slugs(["Pune", "Pune", "Pune Mh 2"], ["MH", "MH", "MH"])


def test_make_slugs_accepts_64_characters_and_rejects_more():
    assert make_slugs(["a" * 64], ["MH"]) == ["a" * 64]
    for length in (65, 70):
        with pytest.raises(ValueError, match="outside the API pattern"):
            make_slugs(["a" * length], ["MH"])


@pytest.mark.parametrize("short", ["पुणे", "X"])  # no ASCII at all; a single character
def test_make_slugs_rejects_a_name_under_two_characters_and_names_only_that_one(short):
    with pytest.raises(ValueError, match=re.escape(f"fewer than 2 characters: ['{short}']")):
        make_slugs(["Pune", short], ["MH", "MH"])


@pytest.mark.parametrize(
    ("names", "states"), [(["Pune", "Nashik"], ["MH"]), (["Pune"], ["MH", "MH"])]
)
def test_make_slugs_rejects_mismatched_lengths(names, states):
    with pytest.raises(ValueError, match="shorter|longer"):  # zip would silently drop a city
        make_slugs(names, states)


@pytest.mark.parametrize(
    ("population", "tier"),
    [(2_500_000, "metro"), (2_499_999, "large"), (1_000_000, "large"), (999_999, "mid")],
)
def test_tier_of(population, tier):
    assert tier_of(population, 2_500_000, 1_000_000) == tier
