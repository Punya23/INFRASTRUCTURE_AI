"""MoRTH press releases: the listing and the PIB release pages (M3 pipeline; skill add-data-source).

The listing is a registry source (`morth_press_releases`). `fetch_press` downloads each listed PIB
release page to data/raw/pib/<PRID>.html — only pages not on disk yet, so the step is also the
incremental refresh — and rewrites the manifest pib_morth_press_releases.yaml. `parse_release` reads
one page. PIB's firewall answers 403 to bot-style agent strings, so requests carry a plain
descriptive one; one request per second, and no robots.txt exists on either site.
"""

from __future__ import annotations

import hashlib
import json
import re
import time
from datetime import UTC, date, datetime

import pandas as pd
import yaml
from lxml import html

from common.fetch import MANIFESTS, FetchError, _get, load_registry
from pipeline.evidence import normalize_text
from pipeline.shared_layers import RAW, ROOT

RAW_PIB = RAW / "pib"
LISTING = RAW / "morth" / "press-release.json"
PAGE_URL = "https://pib.gov.in/PressReleasePage.aspx?PRID={prid}"
PIB_USER_AGENT = "Mozilla/5.0 infra-ai-research (github.com/Punya23/INFRASTRUCTURE_AI)"
PAGE_MARKER = b"innner-page-main-about-us-content-right-part"  # PIB's own spelling; absent on soft-404 pages
THROTTLE_S = 1.1
MONTHS = {m: i for i, m in enumerate(["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"], 1)}


def listing_rows(listing: dict) -> pd.DataFrame:
    """One row per distinct entry of the MoRTH listing: prid (None when the entry has no PIB release
    link), published (YYYY-MM-DD), title, link, file."""
    rows: dict[str, dict] = {}
    for group in listing["page"]["files"]:
        for entry in group.get("files_data") or []:
            link = entry.get("link") or ""
            match = re.search(r"PRID=(\d+)", link)
            prid = match.group(1) if match else None
            key = prid or f"{entry.get('published_date')}|{entry.get('title')}"
            rows.setdefault(key, {"prid": prid, "published": entry.get("published_date"),
                                  "title": (entry.get("title") or "").strip(), "link": link or None,
                                  "file": entry.get("file")})
    # object dtype keeps a missing prid as None (a string column would turn it into NaN)
    return pd.DataFrame(list(rows.values()), columns=["prid", "published", "title", "link", "file"], dtype=object)


def fetch_press() -> None:
    """Fetch the PIB page of every listed release that is not on disk, then write the manifest.
    A page that fails is reported and the rest continue; the step raises at the end so it is not
    mistaken for a clean run."""
    if not LISTING.exists():
        raise FileNotFoundError(f"{LISTING} missing — run: cd ml && uv run python -m common.fetch morth_press_releases")
    rows = listing_rows(json.loads(LISTING.read_text()))
    manifest_path = MANIFESTS / "pib_morth_press_releases.yaml"
    previous = {}
    if manifest_path.exists():
        previous = {f["file"]: f for f in yaml.safe_load(manifest_path.read_text())["files"]}
    RAW_PIB.mkdir(parents=True, exist_ok=True)
    records, failures, fetched = [], [], 0
    for prid in rows["prid"].dropna():
        path, url = RAW_PIB / f"{prid}.html", PAGE_URL.format(prid=prid)
        rel = str(path.relative_to(ROOT))
        if not path.exists():
            try:
                body = _get(url, user_agent=PIB_USER_AGENT)
                if PAGE_MARKER not in body:
                    raise FetchError(f"{url} did not return a release page (got {body[:40]!r})")
            except FetchError as exc:
                failures.append(f"{prid}: {exc}")
                continue
            path.write_bytes(body)
            fetched += 1
            time.sleep(THROTTLE_S)
        data = path.read_bytes()
        sha = hashlib.sha256(data).hexdigest()
        old = previous.get(rel)
        fetched_at = old["fetched_at"] if old and old["sha256"] == sha else datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        records.append({"file": rel, "url": url, "bytes": len(data), "sha256": sha, "fetched_at": fetched_at})
    source = load_registry()["morth_press_releases"]
    manifest = {"id": "pib_morth_press_releases", "license": source["license"],
                "attribution": source["attribution"], "used_by": ["national_highways"], "files": records}
    MANIFESTS.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(yaml.safe_dump(manifest, sort_keys=False, allow_unicode=True))
    print(f"press: {len(rows)} listed, {len(records)} pages on disk ({fetched} fetched now), "
          f"{int(rows['prid'].isna().sum())} without a PIB release link")
    if failures:
        raise FetchError(f"{len(failures)} release pages failed: {failures[:5]}")


def parse_release(raw: bytes) -> dict:
    """Title, posting date, script and paragraphs of a PIB release page.

    Raises ValueError when the page has no release body (a soft-404 page or a layout change).
    `language` is "en" when the title is mostly Latin script and "other" otherwise.
    """
    doc = html.fromstring(raw)
    boxes = doc.xpath('//div[@class="innner-page-main-about-us-content-right-part"]')
    titles = doc.xpath("//h2")
    if not boxes or not titles:
        raise ValueError("no release box or title on the page")
    box = boxes[0]
    stamp = box.xpath('.//div[@id="PrDateTime"]')
    match = re.search(r"(\d{1,2}) ([A-Z]{3}) (\d{4})", stamp[0].text_content() if stamp else "")
    if not match or match.group(2) not in MONTHS:
        raise ValueError("no readable 'Posted On' date")
    posted = date(int(match.group(3)), MONTHS[match.group(2)], int(match.group(1)))
    body = (box.xpath('.//div[@class="WordSection1"]') or [box])[0]
    paragraphs = [text for el in body.iter("p", "li") if (text := normalize_text(el.text_content()))]
    if not paragraphs:
        raise ValueError("release has no body text")
    title = normalize_text(titles[0].text_content())
    letters = [c for c in title if c.isalpha()]
    latin = sum(c.isascii() for c in letters)
    return {"title": title, "posted_on": posted, "paragraphs": paragraphs,
            "language": "en" if letters and latin / len(letters) > 0.7 else "other"}
