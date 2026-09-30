import pytest

from pipeline.evidence import normalize_text, quote_in_source

SOURCE = ("The Cabinet Committee on Economic Affairs, chaired by the Prime Minister Shri Narendra Modi, "
          "today has approved the development of a 4-lane corridor  from Badnawar-Petlawad-Thandla-Timarwani "
          "section of NH-752D\nhaving a length of 80.45 kilometer with a total capital cost of Rs.3,839.42 crore.")


def test_normalize_text_collapses_whitespace_and_unicode():
    assert normalize_text("  a \n b\t c ") == "a b c"
    assert normalize_text("Ｒｓ．１２") == "Rs.12"  # NFKC folds full-width forms


@pytest.mark.parametrize("quote, expected", [
    ("today has approved the development of a 4-lane corridor from Badnawar", True),  # double space in source
    ("section of NH-752D having a length of 80.45 kilometer", True),                  # newline in source
    ("Rs.3,839.42 crore.", True),
    ("today has approved the development of a 6-lane corridor", False),               # a changed number
    ("rs.3,839.42 crore", False),                                                     # case matters
    ("Badnawar–Petlawad", False),                                                     # en dash is not a hyphen
    ("", False),
    ("   ", False),
])
def test_quote_in_source(quote, expected):
    assert quote_in_source(quote, SOURCE) is expected
