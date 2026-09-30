"""Upcoming bus and metro projects from news (ADR-0016; rules and evidence as in ADR-0008, ADR-0012).

    cd ml && APIFY_TOKEN=... uv run python -m fields.public_transport.upcoming fetch   # Apify -> data/raw/apify/
    cd ml && uv run python -m fields.public_transport.upcoming build                    # -> web/fixtures/invest/projects.json

`fetch` runs an Apify actor over the queries in config/fields/upcoming_transport.yaml. `build` reads that
output plus the committed seed (config/upcoming_news_seed.json), and keeps an item only when a stage rule, a
mode rule and a configured city match its own text and the evidence quote is found verbatim in that text.
Everything else is written to data/processed/upcoming_rejects.csv with its reason (AGENTS invariant 2).
The pin sits on the city centre: news names a city, not a site, so geo_precision says "city".
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import UTC, date, datetime
from pathlib import Path
from urllib.parse import urlparse

import yaml

from pipeline.evidence import normalize_text, quote_in_source

ROOT = (
    Path(__file__).resolve().parents[3]
)  # not pipeline.shared_layers: it imports geopandas, which this step never needs
RAW, PROCESSED = ROOT / "data" / "raw", ROOT / "data" / "processed"
CONFIG = ROOT / "config" / "fields" / "upcoming_transport.yaml"
SEED = ROOT / "config" / "upcoming_news_seed.json"
CITIES = ROOT / "web" / "fixtures" / "invest" / "cities.json"
OUT = ROOT / "web" / "fixtures" / "invest" / "projects.json"
RAW_APIFY = RAW / "apify" / "upcoming_news.json"
REJECTS = PROCESSED / "upcoming_rejects.csv"
EXTRACTOR = "rules:upcoming:v1"  # bump when a rule in the config or a regex here changes (ADR-0008)
APIFY_RUN = "https://api.apify.com/v2/acts/{actor}/run-sync-get-dataset-items"
LICENSE = (
    "Headline and link only, stored as metadata under ADR-0012; "
    "copyright of the article stays with its publisher"
)
REJECT_FIELDS = ["url", "title", "reason"]

_COST = re.compile(r"(?:Rs\.?|₹)\s*([\d,]+(?:\.\d+)?)\s*(?:crores?|cr\b)", re.IGNORECASE)
_LENGTH = re.compile(r"(\d[\d,]*(?:\.\d+)?)[\s-]*(?:km|kms|kilomet(?:er|re)s?)\b", re.IGNORECASE)
_URL_DATE = re.compile(r"/(20\d{2})/(\d{2})/(\d{2})/")


class ApifyError(RuntimeError):
    pass


def load_config() -> dict:
    cfg = yaml.safe_load(CONFIG.read_text())
    for rule in cfg["stages"]:
        rule["re"] = re.compile(rule["pattern"], re.IGNORECASE)
    cfg["mode_re"] = {mode: re.compile(p, re.IGNORECASE) for mode, p in cfg["modes"].items()}
    return cfg


# --- fetch ---------------------------------------------------------------------------------------------------


def apify_inputs(cfg: dict) -> list[dict]:
    """Actor inputs, one per batch of queries (one query per template and configured city, newline-separated as
    the actor expects). A single run of every query outlasts Apify's gateway, so each call stays small."""
    cities = {c["id"]: c for c in json.loads(CITIES.read_text())}
    unknown = [i for i in cfg["cities"] if i not in cities]
    if unknown:
        raise ValueError(f"config cities not in cities.json: {unknown}")
    a = cfg["apify"]
    queries = [q.format(city=cities[i]["name"]) for i in cfg["cities"] for q in a["queries"]]
    size = a["queries_per_run"]
    return [
        {
            "queries": "\n".join(queries[i : i + size]),
            "countryCode": a["country_code"],
            "languageCode": a["language_code"],
            "resultsPerPage": a["results_per_page"],
            "maxPagesPerQuery": a["max_pages_per_query"],
        }
        for i in range(0, len(queries), size)
    ]


def fetch_apify() -> None:
    """Run the actor synchronously and store its dataset items. The token is read from APIFY_TOKEN and sent in
    a header, never in the URL. Fails loudly: no token, an HTTP error or a non-list answer stores nothing."""
    token = os.environ.get("APIFY_TOKEN")
    if not token:
        raise ApifyError(
            "APIFY_TOKEN is not set; create one at console.apify.com/settings/integrations"
        )
    cfg = load_config()
    items: list = []
    for batch in apify_inputs(cfg):
        request = urllib.request.Request(
            APIFY_RUN.format(actor=cfg["apify"]["actor"]),
            data=json.dumps(batch).encode(),
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(
                request, timeout=cfg["apify"]["timeout_s"] + 30
            ) as response:
                got = json.load(response)
        except (OSError, urllib.error.HTTPError, json.JSONDecodeError) as exc:
            raise ApifyError(f"Apify run failed: {exc}") from exc
        if not isinstance(got, list):
            raise ApifyError(f"Apify answered {type(got).__name__}, want a list of dataset items")
        items += got  # a failed batch raises above, so nothing is stored from a partial run
    RAW_APIFY.parent.mkdir(parents=True, exist_ok=True)
    RAW_APIFY.write_text(
        json.dumps(
            {
                "source": "apify_news",
                "collected": datetime.now(UTC).date().isoformat(),
                "items": items,
            }
        )
    )
    print(f"   {len(items)} dataset items -> {RAW_APIFY}")


# --- extract -------------------------------------------------------------------------------------------------


def normalise_items(raw: dict) -> list[dict]:
    """Flat news items {title, url, description, date} from a raw file. Accepts the seed's own shape, a Google
    Search dataset (each item holds `organicResults`) and flat news-actor items (title, url or link, snippet)."""
    flat = []
    for item in raw["items"]:
        for hit in item.get("organicResults") or [item]:
            flat.append(
                {
                    "title": (hit.get("title") or "").strip(),
                    "url": (hit.get("url") or hit.get("link") or "").strip(),
                    "description": (hit.get("description") or hit.get("snippet") or "").strip(),
                    "date": hit.get("date") or hit.get("publishedAt"),
                    "source": raw["source"],
                    "fetched_at": raw["collected"],
                }
            )
    return flat


def item_date(item: dict) -> str | None:
    """The publication date when the item states one (ISO date or datetime) or its URL carries /YYYY/MM/DD/."""
    if item["date"]:
        try:
            return datetime.fromisoformat(str(item["date"])).date().isoformat()
        except ValueError:
            pass
    m = _URL_DATE.search(item["url"])
    return date(*map(int, m.groups())).isoformat() if m else None


def _single(values: set[float]) -> float | None:
    """The one value found, or None: two different figures are ambiguous, not averaged."""
    return values.pop() if len(values) == 1 else None


def evidence_for(text: str, pattern: re.Pattern) -> str | None:
    """The first line or sentence of `text` in which the stage rule matches: a verbatim slice of the source."""
    for part in re.split(r"\n|(?<=[.!?])\s+", text):
        if pattern.search(part):
            return part.strip()
    return None


def extract(item: dict, cities: dict[str, dict], cfg: dict) -> tuple[list[dict], str | None]:
    """The projects (one per city named) in one news item, or ([], reason)."""
    if not item["title"] or not item["url"].startswith(("http://", "https://")):
        return [], "no_title_or_link"
    host = urlparse(item["url"]).hostname or ""
    if any(host == d or host.endswith("." + d) for d in cfg["skip_domains"]):
        return [], "not_news_source"
    if re.search(cfg["reference_titles"], item["title"], re.IGNORECASE):
        return [], "reference_page"
    published = item_date(item)
    if (
        published
        and (date.fromisoformat(item["fetched_at"]) - date.fromisoformat(published)).days
        > cfg["max_age_days"]
    ):
        return [], "stale"
    text = f"{item['title']}\n{item['description']}".strip()
    stage_rule = next((r for r in cfg["stages"] if r["re"].search(text)), None)
    if stage_rule is None:
        return [], "no_stage_rule"
    if stage_rule["stage"] == "excluded":
        return [], "not_upcoming"
    modes = [m for m, rx in cfg["mode_re"].items() if rx.search(text)]
    if len(modes) != 1:
        return [], "no_mode" if not modes else "ambiguous_mode"
    named = [c for c in cities.values() if _names_city(text, c)]
    if not named:
        return [], "no_configured_city"
    quote = evidence_for(text, stage_rule["re"])
    if quote is None or not quote_in_source(
        quote, text
    ):  # the check the invariant asks for, done by code
        return [], "quote_not_in_source"
    cost = _single({float(v.replace(",", "")) for v in _COST.findall(quote)})
    length = _single({float(v.replace(",", "")) for v in _LENGTH.findall(quote)})
    w = cfg["confidence"]
    stated = cost is not None or length is not None
    confidence = round(
        w["base"] + w["event_date"] * bool(published) + w["cost_or_length"] * stated, 3
    )
    if confidence < cfg["review_below"]:
        return [], "low_confidence"
    key = hashlib.sha1(item["url"].encode()).hexdigest()[:8]
    return [
        {
            "id": f"{c['id']}-{modes[0]}-{key}",
            "city": c["id"],
            "mode": modes[0],
            "stage": stage_rule["stage"],
            "name": normalize_text(item["title"]),
            "evidence": quote,
            "event_date": published,
            "lat": c["lat"],
            "lon": c["lon"],
            "geo_precision": "city",
            "cost_crore": cost,
            "length_km": length,
            "extractor": EXTRACTOR,
            "source": item["source"],
            "source_ref": item["url"],
            "fetched_at": item["fetched_at"],
            "license": LICENSE,
            "confidence": confidence,
        }
        for c in named
    ], None


def _names_city(text: str, city: dict) -> bool:
    return any(
        re.search(rf"\b{re.escape(n)}\b", text, re.IGNORECASE)
        for n in [city["name"], *city["aliases"]]
    )


# --- build ---------------------------------------------------------------------------------------------------


def build() -> None:
    cfg = load_config()
    all_cities = {c["id"]: c for c in json.loads(CITIES.read_text())}
    unknown = [i for i in cfg["cities"] if i not in all_cities]
    if unknown:
        raise ValueError(f"config cities not in cities.json: {unknown}")
    cities = {i: all_cities[i] for i in cfg["cities"]}
    raws = [json.loads(SEED.read_text())]
    if RAW_APIFY.exists():
        raws.append(json.loads(RAW_APIFY.read_text()))
    projects: dict[
        str, dict
    ] = {}  # upsert on the id, which is city + mode + a hash of the link (invariant 9)
    rejects = []
    for raw in raws:
        for item in normalise_items(raw):
            found, reason = extract(item, cities, cfg)
            if reason:
                rejects.append({"url": item["url"], "title": item["title"], "reason": reason})
            for p in found:
                if p["id"] not in projects or p["confidence"] >= projects[p["id"]]["confidence"]:
                    projects[p["id"]] = p
    ordered = sorted(projects.values(), key=lambda p: (p["city"], p["mode"], p["id"]))
    as_of = max(p["fetched_at"] for p in ordered)
    OUT.write_text(
        json.dumps({"as_of": as_of, "projects": ordered}, indent=1, ensure_ascii=False) + "\n"
    )
    REJECTS.parent.mkdir(parents=True, exist_ok=True)
    with REJECTS.open("w", newline="") as f:
        writer = csv.DictWriter(f, REJECT_FIELDS)
        writer.writeheader()
        writer.writerows(rejects)
    print(f"   {len(ordered)} projects -> {OUT}; {len(rejects)} rejects -> {REJECTS}")


STEPS = {"fetch": fetch_apify, "build": build}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("steps", nargs="+", choices=[*STEPS, "all"])
    args = parser.parse_args(argv)
    try:
        for name in list(STEPS) if "all" in args.steps else args.steps:
            print(f"== {name}", flush=True)
            STEPS[name]()
    except (ApifyError, ValueError, FileNotFoundError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
