"""Guards for the investor flow's copy and markup (web/invest/, web/locales/).

- No returns, yield, profit or forecast language anywhere a visitor can read (ADR-0015: the scores describe
  infrastructure that exists and growth that already happened).
- The pages build all markup through h() and text nodes: no inline scripts or handlers, no innerHTML.
- Every inv.* key a page uses exists in English, and Hindi and Kannada carry the same keys and {tokens}.
"""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WEB = ROOT / "web" / "invest"
BANNED = re.compile(r"\b(returns?|roi|yields?|profit(s|able)?|appreciation|guaranteed)\b", re.IGNORECASE)
STRING_LITERAL = re.compile(r"\"([^\"\n]{3,})\"|'([^'\n]{3,})'|`([^`]{3,})`")
JS_COMMENT = re.compile(r"/\*.*?\*/|(?<![:\w])//[^\n]*", re.DOTALL)  # not the // in https://
LOCALES = ("en", "hi", "kn")
LOOKS_LIKE_CODE = re.compile(r"[;{}]|=>|\n")


def _locale(lang: str) -> dict:
    return json.loads((ROOT / "web" / "locales" / f"{lang}.json").read_text(encoding="utf-8"))


def _visible_text():
    """Text a visitor can read: HTML text nodes, JS string literals, and inv.* locale values.
    JS code itself is skipped, so the `return` keyword is not mistaken for the word."""
    for path in sorted(WEB.rglob("*")):
        if path.suffix == ".html":
            yield path.name, re.sub(r"<[^>]+>", " ", path.read_text(encoding="utf-8"))
        elif path.suffix in {".js", ".mjs"} and not path.name.endswith(".test.mjs"):
            # comments go first: an apostrophe in one would pair with the next quote and capture code
            code = JS_COMMENT.sub("", path.read_text(encoding="utf-8"))
            for m in STRING_LITERAL.finditer(code):
                chunk = next(g for g in m.groups() if g)
                # nested template literals can still pair quotes across code; UI text never has these
                if not LOOKS_LIKE_CODE.search(re.sub(r"\$\{[^}]*\}", " ", chunk)):
                    yield path.name, chunk
    for lang in LOCALES:
        for key, value in _locale(lang).items():
            if key.startswith("inv."):
                yield f"{lang}:{key}", value


def test_guard_catches_what_it_should():
    assert BANNED.search("Expected returns of 12% a year")
    assert BANNED.search("Guaranteed ROI")
    assert not BANNED.search("Access and momentum scores")
    # a comment's apostrophe must not pull code (the `return` keyword) into the scanned text
    assert "return" not in " ".join(
        g for m in STRING_LITERAL.finditer(JS_COMMENT.sub("", "// it's fine\nreturn 'ok text';\n")) for g in m.groups() if g)


def test_no_returns_or_forecast_language():
    hits = [(name, m.group(0)) for name, text in _visible_text() for m in BANNED.finditer(text)]
    assert not hits, hits


def test_pages_use_no_inline_script_and_no_inner_html():
    for path in WEB.rglob("*.html"):
        text = path.read_text(encoding="utf-8").replace("<noscript", "")
        assert not re.search(r"<script(?![^>]*\bsrc=)", text), f"{path.name}: inline script"
        assert not re.search(r"\son[a-z]+=", text), f"{path.name}: inline event handler"
    for path in WEB.rglob("*.js"):
        text = path.read_text(encoding="utf-8")
        assert "innerHTML" not in text and "insertAdjacentHTML" not in text, path.name


def _keys_used_by_pages() -> set[str]:
    """Literal inv.* keys that pages write out in full (data-i18n attributes, tt() calls, dataset entries).
    A key that ends in `.` or is followed by `$` is the start of a template such as `inv.preset.${id}`;
    those are checked through their fixed expansions in the test below."""
    used: set[str] = set()
    for path in WEB.rglob("*"):
        if path.suffix not in {".html", ".js"} or path.name.endswith(".test.mjs"):
            continue
        used |= set(re.findall(r"\b(inv\.[a-z0-9_]+(?:\.[a-z0-9_]+)*)(?![\w.$])", path.read_text(encoding="utf-8")))
    return used


def test_every_key_a_page_uses_exists_in_english():
    en = _locale("en")
    # explain.js completes inv.why / inv.gap, bestAreaText completes inv.sample / inv.state (.best, .best.unnamed)
    prefixes = {"inv.why", "inv.gap", "inv.sample", "inv.state"}
    used = {k for k in _keys_used_by_pages() if k not in prefixes}
    missing = sorted(k for k in used if k not in en)
    assert not missing, missing
    expansions = (
        [f"inv.preset.{p}" for p in ("balanced", "commuter", "highway", "growth")]
        + [f"inv.preset.{p}.desc" for p in ("balanced", "commuter", "highway", "growth")]
        + [f"inv.factor.{f}" for f in ("nh_access", "rail_access", "metro_access", "road_strength", "built_up_growth")]
        + [f"inv.tier.{t}" for t in ("metro", "large", "mid")]
        + [f"inv.scope.{s}" for s in ("metros", "peers", "state", "india")]
        + [f"inv.layer.{layer}" for layer in ("stations", "bus_stops", "highways", "toll_plazas")]
        + [f"inv.error.{e}" for e in ("generic", "timeout", "network", "rate_limited", "not_found")]
    )
    expansions += [f"inv.{p}.{suffix}" for p in ("sample", "state") for suffix in ("best", "best.unnamed")]
    assert [k for k in expansions if k not in en] == []


def test_hindi_and_kannada_have_every_inv_key_with_the_same_tokens():
    en = _locale("en")

    def tokens(s: str) -> list[str]:
        return sorted(re.findall(r"\{\w+\}", s))

    for lang in ("hi", "kn"):
        loc = _locale(lang)
        for key, value in en.items():
            if not key.startswith("inv."):
                continue
            assert key in loc, f"{lang} lacks {key}"
            assert loc[key].strip(), f"{lang}:{key} is empty"
            assert tokens(loc[key]) == tokens(value), f"{lang}:{key} tokens differ from English"
