"""Pure functions that turn OSM and NHAI attributes into canonical National Highways fields.

No I/O here; every rule is covered by tests/test_nh_normalize.py (docs/fields/national-highways.md,
"Canonical mapping" and "Normalization rules").
"""

from __future__ import annotations

import re

import numpy as np
import shapely

ROAD_CLASSES = ("motorway", "trunk", "primary", "secondary", "tertiary")
_NH = re.compile(r"^(?:NH|N\.H\.?)\s*[-–]?\s*0*(\d{1,4})\s*([A-Z]{0,2})$", re.IGNORECASE)
_NE = re.compile(r"^NE\s*[-–]?\s*0*(\d{1,2}|[IVX]{1,4})([A-Z]?)$", re.IGNORECASE)
_NH_LIKE = re.compile(r"^(?:N\.?H|NE)(?![A-Z])", re.IGNORECASE)
_ROMAN = {"I": 1, "II": 2, "III": 3, "IV": 4, "V": 5, "VI": 6, "VII": 7, "VIII": 8, "IX": 9, "X": 10}
_LANES = re.compile(r"^\s*(\d{1,2})\s*(?:L[A-Z]*|lanes?)?\s*$", re.IGNORECASE)


def parse_refs(ref: str | None) -> tuple[list[str], list[str]]:
    """Split an OSM `ref` into normalized NH/NE refs and NH-like tokens that could not be parsed.

    'NH 44;SH 17' -> (['NH44'], []); 'NH-948A' -> (['NH948A'], []); 'NE-II' -> (['NE2'], []);
    'NH44 Bypass' -> ([], ['NH44 Bypass']). Non-NH refs (SH, MDR, …) are ignored.
    """
    if not ref:
        return [], []
    refs: list[str] = []
    rejected: list[str] = []
    for raw in re.split(r"[;,/:]", str(ref)):
        token = raw.strip()
        if not token:
            continue
        if m := _NH.match(token):
            norm = f"NH{int(m.group(1))}{m.group(2).upper()}"
        elif m := _NE.match(token):
            number = m.group(1).upper()
            norm = f"NE{int(number) if number.isdigit() else _ROMAN[number]}{m.group(2).upper()}"
        elif _NH_LIKE.match(token):
            rejected.append(token)
            continue
        else:
            continue
        if norm not in refs:
            refs.append(norm)
    return refs, rejected


def parse_lanes(value: object) -> int | None:
    """OSM `lanes` ('4') or NHAI lane status ('4L', '2LPS') -> total lanes; anything else -> None."""
    if value is None:
        return None
    m = _LANES.match(str(value))
    if not m:
        return None
    lanes = int(m.group(1))
    return lanes if 1 <= lanes <= 16 else None


def classify_osm(tags: dict[str, str]) -> dict | None:
    """Map one OSM way's tags to NH-field attributes, or None if the way is not part of the field.

    motorway ways count on their own (expressways). trunk ways count without an NH/NE ref only when
    they carry no ref at all (OSM India convention: trunk = NH) or an NH-like ref that failed to parse
    (kept so the error is logged); a trunk with another ref — SH 17, a Bangladesh N2 — is not an NH.
    primary/secondary/tertiary ways count only with an NH or NE ref.
    """
    highway = tags.get("highway")
    if highway in ("construction", "proposed"):
        road_class = tags.get(highway)
        status = "under_construction" if highway == "construction" else "proposed"
    else:
        road_class, status = highway, "operational"
    if road_class not in ROAD_CLASSES:
        return None
    refs, rejected = parse_refs(tags.get("ref"))
    expressway = (
        road_class == "motorway" or tags.get("expressway") == "yes" or tags.get("motorroad") == "yes"
    )
    bare_trunk = road_class == "trunk" and (not tags.get("ref") or rejected)
    if not refs and not expressway and not bare_trunk:
        return None
    if refs or road_class == "trunk":
        owner_level = "national"
    else:
        owner_level = "unknown"  # an expressway without a ref may be national or state-built
    return {
        "kind": "expressway_segment" if expressway else "nh_segment",
        "status": status,
        "road_class": road_class,
        "refs": refs,
        "rejected_refs": rejected,
        "ref_missing": not refs,
        "owner_level": owner_level,
        "lanes": parse_lanes(tags.get("lanes")),
        "oneway": tags.get("oneway") in ("yes", "true", "1", "-1"),
        "reversed": tags.get("oneway") == "-1",
        "name": tags.get("name"),
        "old_ref": tags.get("ref:old") or tags.get("old_ref"),
    }


def parse_indian_number(text: str) -> int | None:
    """'1,46,195' (Indian grouping) or '12,123' or '709' -> int; anything else -> None."""
    if not re.fullmatch(r"\d{1,3}(,\d{2,3})*", text.strip()):
        return None
    return int(text.replace(",", ""))


def nhai_status(completion: str | None) -> str | None:
    """NHAI `completion` text -> lifecycle status; None when the text is not recognised."""
    if not isinstance(completion, str) or not completion.strip():
        return None  # None / NaN / empty: unknown, never guessed
    text = completion.strip().lower()
    if re.fullmatch(r"fy\s*-?\s*\d{2}(\s*-\s*\d{2})?", text):  # target completion year: still being built
        return "under_construction"
    if "complet" in text:
        return "operational"
    if "implement" in text or "construct" in text or "progress" in text:
        return "under_construction"
    if "plan" in text or "propos" in text or "dpr" in text:
        return "proposed"
    return None


def lane_band(lanes: object) -> str:
    """Lane count or NHAI lane text -> '<2', '2', '4', '6+' or 'unknown' (for lane-mix tables).

    NHAI 'IL' is an intermediate lane (narrower than two lanes); '2/4 L' style ranges are unknown.
    """
    if isinstance(lanes, str):
        text = lanes.strip().upper()
        if text in ("IL", "<2L", "SL", "1L"):
            return "<2"
        lanes = parse_lanes(re.sub(r"\s*PS$", "", text))
    if lanes is None or (isinstance(lanes, float) and np.isnan(lanes)):
        return "unknown"
    lanes = int(lanes)
    return "<2" if lanes < 2 else "2" if lanes <= 3 else "4" if lanes <= 5 else "6+"


def road_lanes(lanes, weight) -> np.ndarray:
    """Total lanes of the road each way belongs to.

    OSM `lanes` on a one-way carriageway counts that direction only, so one side of a paired dual
    carriageway (weight 0.5 from dual_carriageway_weights) carries half the road's lanes.
    """
    lanes = np.array([np.nan if v is None else float(v) for v in lanes])
    return np.where(np.asarray(weight) == 0.5, lanes * 2, lanes)


def parse_year(value: object) -> int | None:
    """First plausible year (1950–2040) in free text: '2008-11-14', 'January 23, 2008', '2023'."""
    m = re.search(r"\b(19[5-9]\d|20[0-3]\d|2040)\b", str(value)) if value is not None else None
    return int(m.group(1)) if m else None


def _directions(lines: np.ndarray, at: np.ndarray, flip: np.ndarray, step: float = 10.0) -> np.ndarray:
    """Unit travel direction of each line near the point where `at` projects onto it."""
    d = shapely.line_locate_point(lines, at)
    a = shapely.line_interpolate_point(lines, np.maximum(d - step, 0.0))
    b = shapely.line_interpolate_point(lines, np.minimum(d + step, shapely.length(lines)))
    v = np.column_stack([shapely.get_x(b) - shapely.get_x(a), shapely.get_y(b) - shapely.get_y(a)])
    norm = np.linalg.norm(v, axis=1)
    norm[norm == 0] = 1.0
    v = v / norm[:, None]
    v[flip] *= -1
    return v


def dual_carriageway_weights(
    lines: np.ndarray, oneway: np.ndarray, reversed_: np.ndarray, max_gap_m: float = 30.0
) -> np.ndarray:
    """Length weight per way: 0.5 for a one-way carriageway with an opposite-direction partner
    within `max_gap_m` (a divided highway drawn as two ways), else 1.0.

    `lines` must be in a metric CRS. Without this, divided highways count twice.
    """
    lines = np.asarray(lines)
    weights = np.ones(len(lines))
    idx = np.flatnonzero(np.asarray(oneway, dtype=bool))
    if len(idx) < 2:
        return weights
    one = lines[idx]
    flip = np.asarray(reversed_, dtype=bool)[idx]
    mids = shapely.line_interpolate_point(one, 0.5, normalized=True)
    tree = shapely.STRtree(one)
    left, right = tree.query(mids, predicate="dwithin", distance=max_gap_m)
    keep = left != right
    left, right = left[keep], right[keep]
    if len(left) == 0:
        return weights
    own = _directions(one[left], mids[left], flip[left])
    other = _directions(one[right], mids[left], flip[right])
    opposite = (own * other).sum(axis=1) < -0.5
    paired = np.zeros(len(one), dtype=bool)
    paired[left[opposite]] = True
    weights[idx[paired]] = 0.5
    return weights


_OCR_DIGITS = str.maketrans({"]": "1", "l": "1", "I": "1", "|": "1", "O": "0", "o": "0"})
_NUM = r"([\d,\]lIO|o]+)"
_ANNEX_ROW = re.compile(rf"^\S{{1,3}}\s+([A-Za-z&.() ]+?)\s+{_NUM}\s+{_NUM}\s+{_NUM}\s+{_NUM}\s+\S+$")


def ocr_int(token: str) -> int | None:
    """Integer from an OCR'd table cell, fixing digit look-alikes ('4]' -> 41, 'Il' -> 11)."""
    text = token.translate(_OCR_DIGITS).replace(",", "")
    return int(text) if text.isdigit() else None


def parse_rai_annexure(text: str) -> tuple[list[int], list[dict], list[int | None] | None]:
    """OCR text of a Road Accidents in India state annexure ('<serial> <State> <y1..y4> <rank>' rows
    and a 'Total' row) -> (years, rows [{name, values}], totals). Validation is the caller's job."""
    years_m = re.search(r"(\d{4}) to (\d{4})", text)
    years = list(range(int(years_m.group(1)), int(years_m.group(2)) + 1)) if years_m else []
    rows, totals = [], None
    for line in (ln.strip() for ln in text.splitlines()):
        if m := re.match(r"^Total\s+(.+)$", line):
            totals = [ocr_int(t) for t in m.group(1).split()]
        elif m := _ANNEX_ROW.match(line):
            rows.append({"name": m.group(1).strip(), "values": [ocr_int(v) for v in m.groups()[1:]]})
    return years, rows, totals


_PLAZA_NOISE = re.compile(r"\b(toll|tollgate|gate|naka|fee|plaza|plazza|booth|nh|no|new|old|km|ch)\b|[^a-z ]")
_EXPRESSWAY_NOISE = re.compile(r"\b(expressway|corridor|elevated|freeway|flyway|road|bypass)\b|[^a-z ]")


def expressway_key(name: object) -> str:
    """Comparable expressway name: 'Delhi–Meerut Expressway' and 'DELHI-MEERUT EXPY' -> 'delhi meerut'."""
    if not isinstance(name, str):
        return ""
    name = name.replace("–", "-").replace("—", "-").replace("-", " ")
    return " ".join(_EXPRESSWAY_NOISE.sub(" ", name.lower()).split())


def plaza_key(name: object) -> str:
    """Comparable toll-plaza name: 'Bharthana Toll Plaza' and 'BHARTHANA FEE PLAZA (NH-48)' -> 'bharthana'."""
    if not isinstance(name, str):
        return ""
    return " ".join(_PLAZA_NOISE.sub(" ", name.lower()).split())


def plaza_name_score(a: str, b: str) -> float:
    """Similarity of two plaza_key names: 1.0 when every token of one appears in the other
    ('lakhanpur' vs 'lakhanpur rajbagh'), else the difflib ratio."""
    import difflib

    ta, tb = set(a.split()), set(b.split())
    short = ta if len(ta) <= len(tb) else tb
    if short and (short <= ta & tb) and max(map(len, short)) >= 4:
        return 1.0
    return difflib.SequenceMatcher(None, a, b).ratio()
