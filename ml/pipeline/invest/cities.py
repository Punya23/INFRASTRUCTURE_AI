"""City definition (spec §5): urban centres (UN Degree of Urbanisation) cut at state borders.

Pure functions; the raster and GeoNames loading lives in the CLI step that calls them.
"""

from __future__ import annotations

import re
import unicodedata
from collections import Counter

import numpy as np
import pandas as pd
from affine import Affine

_OFFSETS = {
    4: [(-1, 0), (0, -1), (0, 1), (1, 0)],
    8: [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)],
}
# Cells outside every state polygon borrow a state from their neighbours for at most this many
# rounds: coastline/border slivers are at most 2 cells wide at 1 km and 3 rounds reach 3 cells
# (team judgment, 2026-09-29). A cap on the algorithm, not a tunable threshold, so not in config.
_STATE_FILL_ROUNDS = 3
_NAMING_COLUMNS = ["name", "geonameid", "lat", "lon", "aliases", "review"]
_CITY_ID = re.compile(r"[a-z0-9-]{2,64}")  # the API's city id contract, api/openapi.yaml


def _fill_unknown_state(
    state_ids: np.ndarray, mask: np.ndarray, offsets: list[tuple[int, int]]
) -> np.ndarray:
    """Urban cells with state id 0 (coastline or simplified border) take the state their urban
    neighbours agree on, for up to _STATE_FILL_ROUNDS rounds. Neighbours that are not urban give
    nothing, and neighbours that disagree leave the cell at 0: unknown, never a guess.
    """
    state = state_ids.copy()
    for _ in range(_STATE_FILL_ROUNDS):
        rows, cols = np.nonzero(mask & (state == 0))
        if not len(rows):
            break
        voters = np.pad(np.where(mask, state, 0), 1)  # only urban cells with a known state vote
        vote = np.zeros(len(rows), dtype=state.dtype)
        disagree = np.zeros(len(rows), dtype=bool)
        for dr, dc in offsets:
            neighbour = voters[rows + 1 + dr, cols + 1 + dc]
            disagree |= (neighbour != 0) & (vote != 0) & (neighbour != vote)
            vote = np.where(vote == 0, neighbour, vote)
        take = (vote != 0) & ~disagree
        state[rows[take], cols[take]] = vote[take]
    return state


def label_urban_centres(
    density: np.ndarray, state_ids: np.ndarray, min_density: float, connectivity: int = 8
) -> tuple[np.ndarray, dict[int, int]]:
    """Label contiguous cells with density >= min_density; never let a label cross a state border.

    NaN density is background, even when min_density is 0. Returns (labels, label_state): labels
    are 1.. (0 = background), label_state maps label -> state id. State id 0 means unknown: no
    state polygon covers the centre, or the states around it disagree (see _fill_unknown_state).
    The cities step routes such pieces to review; it never guesses a state.
    """
    if density.shape != state_ids.shape:
        raise ValueError("density and state_ids must have the same shape")
    if connectivity not in _OFFSETS:
        raise ValueError("connectivity must be 4 or 8")
    mask = density >= min_density  # NaN >= x is False, so NaN is background
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


def assign_places(places: pd.DataFrame, labels: np.ndarray, transform: Affine) -> pd.DataFrame:
    """Add `label` (0 = outside every urban centre) to places with `lon`/`lat`, by the raster cell.

    A place off the grid, or with a NaN or infinite coordinate, is outside: it is never guessed
    onto a cell.
    """
    lon = places["lon"].to_numpy(dtype=float)
    lat = places["lat"].to_numpy(dtype=float)
    located = np.isfinite(lon) & np.isfinite(lat)
    # NaN in, NaN out: it fails every bound below, so nothing non-finite is ever cast to an index
    cols, rows = ~transform @ (np.where(located, lon, np.nan), np.where(located, lat, np.nan))
    rows, cols = np.floor(rows), np.floor(cols)
    inside = (rows >= 0) & (rows < labels.shape[0]) & (cols >= 0) & (cols < labels.shape[1])
    out = places.copy()
    out["label"] = 0
    out.loc[inside, "label"] = labels[rows[inside].astype(int), cols[inside].astype(int)]
    return out


def name_pieces(
    pieces: pd.DataFrame, places: pd.DataFrame, overrides: dict[int, str], big_place: int
) -> pd.DataFrame:
    """Name each piece after its anchor place; adds name, geonameid, lat, lon, aliases and review.

    Anchor: the largest place in the piece that an override names, else the largest place (a tie
    goes to the lower geonameid). If overrides name several places in one piece, the larger place's
    override wins and the others stay in the piece as aliases. The piece takes the anchor's override
    name, if it has one.

    aliases: the anchor's GeoNames name when an override renamed it (so a search for the old name
    still finds the piece), then every other place with at least `big_place` people or an override,
    largest first, each under its override name if it has one.
    review: two or more places reach `big_place`, so a human looks at the piece.

    A piece with no place gets name None, geonameid <NA> and lat/lon NaN: the caller reviews and
    skips it. An override id that lies in no piece is stale config and raises ValueError.

    `big_place` has no default: it is config (cities.alias_min_population), never a constant here.
    """
    placed = {int(g) for g in places.loc[places["label"].isin(pieces["label"]), "geonameid"]}
    stale = sorted(set(overrides) - placed)
    if stale:
        raise ValueError(f"name_overrides ids that lie in no piece: {stale}")
    rows = []
    for piece in pieces.itertuples():
        inside = places[places["label"] == piece.label].sort_values(
            ["population", "geonameid"], ascending=[False, True]
        )
        row = {
            "name": None,
            "geonameid": None,
            "lat": None,
            "lon": None,
            "aliases": [],
            "review": False,
        }
        if len(inside):
            big = inside["population"] >= big_place
            named = inside["geonameid"].isin(list(overrides))
            anchor = inside[named].iloc[0] if named.any() else inside.iloc[0]
            shown = overrides.get(int(anchor["geonameid"]), anchor["name"])
            others = inside[(big | named) & (inside["geonameid"] != anchor["geonameid"])]
            aliases = [
                str(overrides.get(int(g), n)) for g, n in zip(others["geonameid"], others["name"])
            ]
            if shown != anchor["name"]:
                aliases.insert(0, str(anchor["name"]))
            row.update(
                name=shown,
                geonameid=int(anchor["geonameid"]),
                lat=float(anchor["lat"]),
                lon=float(anchor["lon"]),
                aliases=aliases,
                review=bool(big.sum() >= 2),
            )
        rows.append(row)
    # object dtype keeps a missing name None (pandas 3 would make it NaN); the other columns get
    # types that hold a gap without turning an id into a float ("10.0" would break a source_ref)
    added = pd.DataFrame(rows, columns=_NAMING_COLUMNS, dtype=object).astype(
        {"geonameid": "Int64", "lat": float, "lon": float, "review": bool}
    )
    return pd.concat([pieces.reset_index(drop=True), added], axis=1)


def _slug(name: str) -> str:
    ascii_name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", ascii_name.lower()).strip("-")


def make_slugs(names: list[str], state_codes: list[str]) -> list[str]:
    """Deterministic ids: the slug; on a collision every colliding city gets `-<state>`; then `-2`,
    `-3` in input order, so the caller must pass a stable order.

    Raises ValueError rather than return an id the API would reject or one id for two cities: a
    name with fewer than 2 ASCII characters, a duplicate id, or an id outside the API's pattern.
    """
    base = [_slug(n) for n in names]
    short = [n for n, b in zip(names, base) if len(b) < 2]
    if short:
        raise ValueError(f"names that slugify to fewer than 2 characters: {short}")
    counts = Counter(base)
    slugs = [
        b if counts[b] == 1 else f"{b}-{s.lower()}" for b, s in zip(base, state_codes, strict=True)
    ]
    seen: Counter = Counter()
    out = []
    for s in slugs:
        seen[s] += 1
        out.append(s if seen[s] == 1 else f"{s}-{seen[s]}")
    duplicates = sorted(s for s, k in Counter(out).items() if k > 1)  # a city named "Pune Mh 2"
    if duplicates:
        raise ValueError(f"duplicate city ids: {duplicates}")
    invalid = [s for s in out if not _CITY_ID.fullmatch(s)]
    if invalid:
        raise ValueError(f"city ids outside the API pattern {_CITY_ID.pattern}: {invalid}")
    return out


def tier_of(population: float, metro_min: float, large_min: float) -> str:
    return "metro" if population >= metro_min else "large" if population >= large_min else "mid"
