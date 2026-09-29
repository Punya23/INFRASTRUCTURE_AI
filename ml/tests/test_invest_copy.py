"""Copy and markup guards for the investor pages (web/invest/) and their locale strings.

Scores describe existing infrastructure and past growth; nothing on these pages may read like a return,
price or forecast claim, and pages must load code only through module scripts (no inline script or handler,
no innerHTML with data).
"""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
INVEST = ROOT / "web" / "invest"
BANNED = re.compile(
    r"\b(returns?|roi|yields?|profit(s|able)?|appreciation|guaranteed)\b", re.IGNORECASE
)
STRING_LITERAL = re.compile(r"\"([^\"\n]{3,})\"|'([^'\n]{3,})'|`([^`]{3,})`")


def _visible_text():
    """Text a visitor can read: HTML text nodes, JS string literals, and inv.* locale values.
    JS code itself is skipped, so the `return` keyword is not mistaken for the word."""
    for path in sorted(INVEST.rglob("*")):
        if path.suffix == ".html":
            yield path.name, re.sub(r"<[^>]+>", " ", path.read_text(encoding="utf-8"))
        elif path.suffix in {".js", ".mjs"} and not path.name.endswith(".test.mjs"):
            for m in STRING_LITERAL.finditer(path.read_text(encoding="utf-8")):
                yield path.name, next(g for g in m.groups() if g)
    for lang in ("en", "hi", "kn"):
        data = json.loads((ROOT / "web" / "locales" / f"{lang}.json").read_text(encoding="utf-8"))
        for key, value in data.items():
            if key.startswith("inv."):
                yield f"{lang}:{key}", value


def test_guard_catches_what_it_should():
    assert BANNED.search("Expected returns of 12% a year")
    assert BANNED.search("Guaranteed ROI")
    assert BANNED.search("A high-yield area with steady profit")
    assert not BANNED.search("Access and momentum scores")


def test_no_returns_or_forecast_language():
    hits = [(name, m.group(0)) for name, text in _visible_text() for m in BANNED.finditer(text)]
    assert not hits, hits


def test_the_guard_scans_every_locale_and_page():
    names = {name for name, _ in _visible_text()}
    assert {"index.html", "start.html", "state.html", "city.html", "city.js"} <= names
    for lang in ("en", "hi", "kn"):
        assert any(n.startswith(f"{lang}:inv.") for n in names), lang


def test_pages_use_no_inline_script_and_no_inner_html():
    pages = sorted(INVEST.rglob("*.html"))
    assert len(pages) == 4
    for path in pages:
        text = path.read_text(encoding="utf-8")
        assert not re.search(r"<script(?![^>]*\bsrc=)", text), f"{path.name}: inline script"
        assert not re.search(r"\son[a-z]+\s*=", text), f"{path.name}: inline event handler"
    for path in INVEST.rglob("*.js"):
        text = path.read_text(encoding="utf-8")
        assert "innerHTML" not in text and "insertAdjacentHTML" not in text, path.name
