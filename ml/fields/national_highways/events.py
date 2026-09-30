"""Cited NH project events from MoRTH press releases on PIB (M3; ADR-0008, ADR-0012).

Rules, not a model: a release becomes an event only if its title matches a rule in
config/fields/national_highways.yaml and one sentence of its opening paragraphs states the stage.
That sentence is the evidence quote — copied verbatim and re-checked against the page — and every
other field (NH refs, states, cost, length) is read from the title and the quote alone, so it can be
cited. Anything that fails goes to the review queue; every listed release, event or not, appears in
press_releases.csv with its reason (AGENTS.md invariants 1–3).
"""

from __future__ import annotations

import json
import re
from datetime import date

import pandas as pd
import yaml

from fields.national_highways.build import OUT
from fields.national_highways.ingest_pib import (
    LISTING,
    PAGE_URL,
    RAW_PIB,
    listing_rows,
    parse_release,
)
from pipeline.evidence import normalize_text, quote_in_source
from pipeline.shared_layers import CANONICAL_STATES, ROOT

SOURCE = "pib_morth"
EXTRACTOR = "rules:nh_events:v1"  # bump when a rule or a regex changes (ADR-0008: the extractor is stored)
LIFECYCLE = ("proposed", "approved", "tendered", "under_construction", "operational", "stalled", "cancelled")
EVENT_FIELDS = [
    "id", "source", "source_ref", "source_url", "fetched_at", "license", "event_type", "stage", "event_date",
    "name", "nh_refs", "states", "cost_crore", "length_km", "modes", "evidence", "language", "extractor",
    "confidence", "reasons",
]

_NH_ABBREV = re.compile(r"\bNH\)?\s*[-–]?\s*(\d{1,3})(?:\s?([A-Z]{1,2})\b)?")
_NH_LONG = re.compile(r"\bNational Highway[-\s]*(?:\(NH\)[-\s]*)?(\d{1,3})([A-Z]{0,2})\b")
_STATE_NAME = "(?:" + "|".join(re.escape(s) for s in sorted(CANONICAL_STATES, key=len, reverse=True)) + r")(?![-–\w])"
_IN_STATES = re.compile(  # "in Bihar", "across Jammu and Kashmir and Ladakh", "in Uttar Pradesh and Haryana"
    rf"\b(?:in|In|across|Across)\s+(?:the\s+)?(?:[Ss]tates?\s+of\s+)?({_STATE_NAME}(?:\s*(?:,|and)\s*{_STATE_NAME})*)")
_STATES_IN_LIST = re.compile(_STATE_NAME)
_COST = re.compile(r"(?:Rs\.?|₹)\s*([\d,]+(?:\.\d+)?)\s*(?:crores?|cr\b)", re.IGNORECASE)
_LENGTH = re.compile(r"(\d[\d,]*(?:\.\s?\d+)?)\s*(?:km|kms|kilomet(?:er|re)s?)\b", re.IGNORECASE)
_MODES = {"HAM": r"\bHAM\b|Hybrid Annuity", "BOT": r"\bBOT\b|Build[- ]Operate[- ]Transfer",
          "EPC": r"\bEPC\b", "TOT": r"\bTOT\b"}
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+(?=[A-Z₹“\"'(])")


def extract_nh_refs(text: str) -> list[str]:
    """NH refs in order of appearance, normalised: 'NH-752D', 'National Highway (NH)-63' and
    'NH 248 BB' give NH752D, NH63 and NH248BB."""
    found = [(m.start(), f"NH{int(m.group(1))}{(m.group(2) or '').upper()}") for m in _NH_ABBREV.finditer(text)]
    found += [(m.start(), f"NH{int(m.group(1))}{m.group(2).upper()}") for m in _NH_LONG.finditer(text)]
    return list(dict.fromkeys(ref for _, ref in sorted(found)))


def extract_states(text: str) -> list[str]:
    """Canonical states the text places a project in, in order: only names introduced by 'in' or
    'across' count, so a corridor name ('Delhi Mumbai expressway', 'Delhi–Meerut') is not a state."""
    found = [s for m in _IN_STATES.finditer(text.replace("&", "and")) for s in _STATES_IN_LIST.findall(m.group(1))]
    return list(dict.fromkeys(found))


def _single(values: set[float]) -> float | None:
    """The one value found, or None — two different figures in a quote are ambiguous, not averaged."""
    return values.pop() if len(values) == 1 else None


def extract_cost_crore(text: str) -> float | None:
    return _single({float(m.replace(",", "")) for m in _COST.findall(text)})


def extract_length_km(text: str) -> float | None:
    return _single({float(m.replace(",", "").replace(" ", "")) for m in _LENGTH.findall(text)})


def extract_modes(text: str) -> list[str]:
    return [mode for mode, pattern in _MODES.items() if re.search(pattern, text)]


def evidence_sentence(paragraphs: list[str], pattern: re.Pattern, max_chars: int, opening: int) -> str | None:
    """First sentence of the first `opening` paragraphs that matches `pattern`, cut to a verbatim prefix of
    at most `max_chars` (on a word boundary) when longer. None if none matches or the cut loses the match."""
    for paragraph in paragraphs[:opening]:
        for sentence in _SENTENCE_END.split(paragraph):
            if pattern.search(sentence):
                if len(sentence) > max_chars:
                    sentence = sentence[:max_chars].rsplit(" ", 1)[0]
                return sentence if pattern.search(sentence) else None
    return None


def confidence(event: dict, cfg: dict) -> float:
    w = cfg["confidence"]
    return round(w["base"] + w["nh_ref"] * bool(event["nh_refs"]) + w["state"] * bool(event["states"])
                 + w["cost"] * (event["cost_crore"] is not None), 3)


def extract_event(release: dict, rule: dict, cfg: dict) -> tuple[dict | None, str | None]:
    """Event fields for a release whose title matched `rule`, or (None, reason)."""
    quote = evidence_sentence(release["paragraphs"], re.compile(rule["evidence"], re.IGNORECASE),
                              cfg["evidence_max_chars"], cfg["opening_paragraphs"])
    if quote is None:
        return None, "no_evidence_sentence"
    cited = f"{release['title']}\n{quote}"  # a field counts only if the title or the quote states it
    event = {
        "event_type": rule["type"], "stage": rule["stage"], "event_date": release["posted_on"].isoformat(),
        "name": release["title"], "nh_refs": extract_nh_refs(cited), "states": extract_states(cited),
        "cost_crore": extract_cost_crore(cited), "length_km": extract_length_km(cited),
        "modes": extract_modes(cited), "evidence": quote, "language": "en", "extractor": EXTRACTOR,
    }
    event["confidence"] = confidence(event, cfg)
    return event, None


def _title_key(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", normalize_text(title).casefold())


def verify_event(event: dict, release: dict, listed: dict, cfg: dict) -> list[str]:
    """Reasons an event goes to the review queue instead of the dataset (empty = verified)."""
    problems = []
    if not quote_in_source(event["evidence"], "\n".join(release["paragraphs"])):
        problems.append("quote_not_in_source")
    if event["stage"] not in LIFECYCLE:
        problems.append("stage_not_in_lifecycle")
    if not (event["nh_refs"] or event["states"] or event["cost_crore"]):
        problems.append("no_anchor")  # nothing ties the event to a road, a state or a project cost
    published = date.fromisoformat(listed["published"]) if listed["published"] else None
    if published is None or abs((release["posted_on"] - published).days) > cfg["max_listing_date_gap_days"]:
        problems.append("listing_date_mismatch")
    listed_key, page_key = _title_key(listed["title"]), _title_key(release["title"])
    if not listed_key or not (listed_key in page_key or page_key in listed_key):  # the listing shortens titles
        problems.append("listing_title_mismatch")
    if event["confidence"] < cfg["review_below"]:
        problems.append("low_confidence")
    return problems


def classify_release(listed: dict, fetched: dict[str, str], rules: list, cfg: dict) -> tuple[str, dict | None, list[str]]:
    """(classification, event or None, reasons) for one listed release. Every branch is explicit."""
    prid = listed["prid"]
    if prid is None:
        return "no_release_text", None, ["no_pib_release_link"]
    path = RAW_PIB / f"{prid}.html"
    if not path.exists():
        return "not_fetched", None, ["page_not_on_disk"]
    try:
        release = parse_release(path.read_bytes())
    except ValueError as exc:
        return "unparsed", None, [str(exc)]
    if release["language"] not in cfg["languages"]:
        return "unsupported_language", None, [f"language_{release['language']}"]
    for title_rx, rule in rules:
        if title_rx.search(release["title"]):
            event, reason = extract_event(release, rule, cfg)
            if event is None:
                return "review", None, [reason]
            event.update({"id": f"nh_project_event:{SOURCE}:{prid}", "source": SOURCE, "source_ref": prid,
                          "source_url": PAGE_URL.format(prid=prid), "fetched_at": fetched.get(prid)})
            problems = verify_event(event, release, listed, cfg)
            return ("review" if problems else "event"), event, problems
    return "no_project_event", None, []


def build_events() -> pd.DataFrame:
    """Classify every listed MoRTH release; write press_releases.csv, nh_events.parquet (verified
    events) and nh_events_review.csv (a rule matched but verification failed)."""
    cfg = yaml.safe_load((ROOT / "config" / "fields" / "national_highways.yaml").read_text())["events"]
    rules = [(re.compile(r["title"], re.IGNORECASE), r) for r in cfg["rules"]]
    manifest_path = ROOT / "data" / "manifests" / "pib_morth_press_releases.yaml"
    if not manifest_path.exists():
        raise FileNotFoundError(f"{manifest_path} missing — run: cd ml && uv run python -m fields.national_highways press")
    manifest = yaml.safe_load(manifest_path.read_text())
    fetched = {f["file"].rsplit("/", 1)[-1].removesuffix(".html"): f["fetched_at"] for f in manifest["files"]}
    listing = listing_rows(json.loads(LISTING.read_text()))

    releases, events, review = [], [], []
    for listed in listing.to_dict("records"):
        classification, event, reasons = classify_release(listed, fetched, rules, cfg)
        releases.append({"prid": listed["prid"], "published": listed["published"], "title": listed["title"],
                         "link": listed["link"], "classification": classification,
                         "event_type": event["event_type"] if event else None, "reasons": ";".join(reasons)})
        if event is not None:
            (review if reasons else events).append(
                {**event, "license": manifest["license"], "reasons": ";".join(reasons)})
    OUT.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(releases).to_csv(OUT / "press_releases.csv", index=False)
    verified = pd.DataFrame(events, columns=EVENT_FIELDS)
    verified.to_parquet(OUT / "nh_events.parquet")
    pd.DataFrame(review, columns=EVENT_FIELDS).to_csv(OUT / "nh_events_review.csv", index=False)
    counts = pd.DataFrame(releases)["classification"].value_counts().to_dict()
    print(f"events: {len(listing)} listed releases -> {counts}; {len(verified)} verified, {len(review)} in review")
    return verified
