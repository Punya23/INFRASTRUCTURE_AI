"""Upcoming bus and metro projects from news: rules, evidence check, fail-closed rejects (ADR-0016)."""

import json

import pytest

from fields.public_transport import upcoming as up

CFG = up.load_config()
CITIES = {c["id"]: c for c in json.loads(up.CITIES.read_text()) if c["id"] in CFG["cities"]}


def item(title, url="https://example.test/a", description="", date=None):
    return {
        "title": title,
        "url": url,
        "description": description,
        "date": date,
        "source": "test",
        "fetched_at": "2026-09-30",
    }


@pytest.mark.parametrize(
    "title,stage,mode",
    [
        ("Hyderabad Metro Phase 2B Gets Cabinet Approval", "approved", "metro"),
        ("DPRs for Jammu and Srinagar metrolite projects submitted to Centre", "proposed", "metro"),
        ("Srinagar Metro Project Stuck in Administrative Limbo", "stalled", "metro"),
        ("Infrastructure for 200 e-Buses underway in Srinagar", "under_construction", "bus"),
        ("Pune BRT tender invited for new corridor", "tendered", "bus"),
    ],
)
def test_stage_and_mode_rules(title, stage, mode):
    projects, reason = up.extract(item(title), CITIES, CFG)
    assert reason is None and projects[0]["stage"] == stage and projects[0]["mode"] == mode


def test_one_project_per_city_named_with_the_quote_verbatim_in_the_source():
    title = "DPRs for Jammu and Srinagar metrolite projects submitted to Centre"
    projects, _ = up.extract(item(title), CITIES, CFG)
    assert sorted(p["city"] for p in projects) == ["jammu", "srinagar"]
    assert all(p["evidence"] in title and p["geo_precision"] == "city" for p in projects)
    assert len({p["id"] for p in projects}) == 2  # ids differ by city, so the upsert keeps both


@pytest.mark.parametrize(
    "title,reason",
    [
        ("Mumbai Metro lines 9 and 2B inaugurated for commuters", "not_upcoming"),  # already open
        ("Coimbatore metro proposal rejected by Centre", "not_upcoming"),  # turned down
        ("Delhi weather turns cold", "no_stage_rule"),
        ("Delhi metro feeder buses approved", "ambiguous_mode"),  # metro and bus in one item
        ("Cabinet approves metro for Atlantis", "no_configured_city"),
        ("", "no_title_or_link"),
    ],
)
def test_items_that_fail_go_to_rejects_with_a_reason(title, reason):
    assert up.extract(item(title), CITIES, CFG) == ([], reason)


def test_social_posts_and_old_reports_are_not_projects():
    social = item("Pune metro approved", url="https://www.instagram.com/reel/x/")
    assert up.extract(social, CITIES, CFG) == ([], "not_news_source")
    old = item("Pune metro approved", date="2020-12-15T12:00:00.000Z")
    assert up.extract(old, CITIES, CFG) == ([], "stale")
    assert up.extract(item("Pune metro approved", date="2026-08-01"), CITIES, CFG)[1] is None


def test_link_must_be_http():
    assert up.extract(item("Pune metro approved", url="javascript:alert(1)"), CITIES, CFG) == (
        [],
        "no_title_or_link",
    )


def test_cost_length_and_date_are_read_only_from_the_evidence_and_the_item():
    p, _ = up.extract(
        item(
            "Srinagar Metro: DPR worth Rs 4,893 crore for 25-km line awaits nod",
            date="2026-04-02T10:00:00Z",
        ),
        CITIES,
        CFG,
    )
    assert (p[0]["cost_crore"], p[0]["length_km"], p[0]["event_date"]) == (
        4893.0,
        25.0,
        "2026-04-02",
    )
    p, _ = up.extract(item("Pune metro: 10 km or 12 km line approved"), CITIES, CFG)
    assert p[0]["length_km"] is None  # two figures are ambiguous, never averaged
    p, _ = up.extract(
        item("Pune metro approved", url="https://x.test/2026/03/05/pune"), CITIES, CFG
    )
    assert p[0]["event_date"] == "2026-03-05"


def test_normalise_items_reads_google_search_and_flat_shapes():
    raw = {
        "source": "apify_news",
        "collected": "2026-09-30",
        "items": [
            {
                "searchQuery": {"term": "q"},
                "organicResults": [{"title": "A", "url": "https://a.test", "description": "d"}],
            },
            {"title": "B", "link": "https://b.test", "snippet": "s", "publishedAt": "2026-01-02"},
        ],
    }
    got = up.normalise_items(raw)
    assert [(g["title"], g["url"], g["description"]) for g in got] == [
        ("A", "https://a.test", "d"),
        ("B", "https://b.test", "s"),
    ]


def test_fetch_without_a_token_fails_closed(monkeypatch):
    monkeypatch.delenv("APIFY_TOKEN", raising=False)
    with pytest.raises(up.ApifyError, match="APIFY_TOKEN"):
        up.fetch_apify()


def test_apify_inputs_split_every_query_into_small_batches():
    batches = up.apify_inputs(CFG)
    queries = [q for b in batches for q in b["queries"].split("\n")]
    assert len(queries) == len(CFG["cities"]) * len(CFG["apify"]["queries"])
    assert all(len(b["queries"].split("\n")) <= CFG["apify"]["queries_per_run"] for b in batches)


def test_committed_fixture_matches_the_seed():
    """projects.json is what `build` makes from the committed seed: re-run it if this fails."""
    seed = up.normalise_items(json.loads(up.SEED.read_text()))
    want = {p["id"] for i in seed for p in up.extract(i, CITIES, CFG)[0]}
    have = {p["id"] for p in json.loads(up.OUT.read_text())["projects"]}
    assert want <= have
