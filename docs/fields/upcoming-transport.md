# Upcoming bus and metro projects (news)

Part of the metro rail and public transport work; decision in [ADR-0016](../adr/0016-apify-news-for-upcoming-transport.md).

```bash
cd ml && APIFY_TOKEN=... uv run python -m fields.public_transport.upcoming fetch   # Apify -> data/raw/apify/upcoming_news.json
cd ml && uv run python -m fields.public_transport.upcoming build                    # seed + Apify -> web/fixtures/invest/projects.json
```

- **Config:** `config/fields/upcoming_transport.yaml` (cities searched, actor and queries, stage and mode rules, confidence weights).
- **Seed:** `config/upcoming_news_seed.json`, headlines and links from web searches on 2026-09-30. Items whose status a later report contradicts, or whose target date has passed, were left out on purpose.
- **Output:** `projects.json` (served at `/v1/cities/{id}/projects`); rejects with reasons in `data/processed/upcoming_rejects.csv`.
- **Reading a project:** `stage` is one of proposed, approved, tendered, under_construction, stalled. `evidence` is text found verbatim in the item. `geo_precision: city` means the pin is the city centre.
- **Adding a city:** add its id (from `web/fixtures/invest/cities.json`) to `cities:`, run `fetch` and `build`.
