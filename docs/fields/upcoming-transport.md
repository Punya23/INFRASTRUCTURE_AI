# Upcoming bus and metro projects (news)

Part of the metro rail and public transport work; decision in [ADR-0016](../adr/0016-apify-news-for-upcoming-transport.md).

```bash
cd ml && APIFY_TOKEN=... uv run python -m fields.public_transport.upcoming fetch   # Apify -> data/raw/apify/upcoming_news.json
cd ml && uv run python -m fields.public_transport.upcoming build                    # seed + Apify -> web/fixtures/invest/projects.json
```

- **Config:** `config/fields/upcoming_transport.yaml` (cities searched, actor and queries, stage and mode rules, confidence weights).
- **Filters:** `skip_domains` (social, forums, wikis), `reference_titles` (route-map and portal pages), `max_age_days` (dated items only). Each reject and its reason is in the rejects file. The fetch runs in batches of `queries_per_run` because one call for every query times out at Apify's gateway.
- **Seed:** `config/upcoming_news_seed.json`, headlines and links from web searches on 2026-09-30. Items whose status a later report contradicts, or whose target date has passed, were left out on purpose.
- **Output:** `projects.json` (served at `/v1/cities/{id}/projects`); rejects with reasons in `data/processed/upcoming_rejects.csv`.
- **Reading a project:** `stage` is one of proposed, approved, tendered, under_construction, stalled. `evidence` is text found verbatim in the item. `geo_precision: city` means the pin is the city centre.
- **Adding a city:** add its id (from `web/fixtures/invest/cities.json`) to `cities:`, run `fetch` and `build`.
