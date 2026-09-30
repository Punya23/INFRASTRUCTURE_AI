"""Evidence check shared by every extractor (ADR-0008, AGENTS.md invariant 3).

A claim pulled out of text is kept only if its quote appears verbatim in the source. Code does the
check, after normalising Unicode and whitespace, so a paraphrase — or a model's invention — fails.
"""

from __future__ import annotations

import unicodedata


def normalize_text(text: str) -> str:
    """NFKC, then every run of whitespace collapsed to one space — the form quotes are compared in."""
    return " ".join(unicodedata.normalize("NFKC", text).split())


def quote_in_source(quote: str, source_text: str) -> bool:
    """True when `quote` is non-empty and appears verbatim (case-sensitive) in `source_text`."""
    needle = normalize_text(quote)
    return bool(needle) and needle in normalize_text(source_text)
