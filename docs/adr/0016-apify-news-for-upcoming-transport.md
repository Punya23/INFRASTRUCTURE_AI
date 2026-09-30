# ADR-0016: Apify to find upcoming bus and metro projects in news

- Status: Proposed
- Date: 2026-09-30
- Deciders: project team
- Related: docs/PLAN.md §7 · ADR-0008, ADR-0011, ADR-0012, ADR-0013, ADR-0015

## Context

The investor city page shows what exists (stations, bus stops) but not what is coming. Upcoming bus and metro projects are announced in news long before OSM or an operator feed shows them. Scraping news sites one by one is brittle and their terms differ; Apify runs maintained scraper "actors" behind one HTTP API. Invariant 12 asks for an ADR before any new service.

## Decision

- **Apify is a fetch tool, called over its REST API with the standard library.** `ml/fields/public_transport/upcoming.py fetch` POSTs to the actor's `run-sync-get-dataset-items` endpoint and stores the answer under `data/raw/apify/`. No Apify SDK, no new Python dependency. The actor (default `apify~google-search-scraper`), the query templates and the cities live in `config/fields/upcoming_transport.yaml`; the token is `APIFY_TOKEN` in the environment, sent in a header, never in the URL, a file or a log. Without a token, `fetch` fails closed and stores nothing.
- **Rules extract, code verifies (ADR-0008).** A headline or snippet becomes a project only when a stage rule, exactly one mode rule (metro or bus) and a configured city name match its own text, and the evidence quote is found verbatim in that text. Cost and length are read only from the quote and only when there is exactly one figure. Everything else, including items already open or turned down, goes to `data/processed/upcoming_rejects.csv` with a reason. No model is involved; a model-assisted extractor would be one function behind the same check.
- **Stored under ADR-0012.** Headline (as the publisher wrote it), link and the short evidence text; never the article. The pin sits at the city centre with `geo_precision: "city"`, because news names a city, not a site; the UI says so.
- **Served as one more endpoint.** `web/fixtures/invest/projects.json` is loaded and validated by the Go store (fail closed: unknown city, stage or mode, missing evidence or provenance, a source that is not a link) and served at `GET /v1/cities/{id}/projects`. The city page draws one badge per mode on the map and lists every project with its quote and link.
- **Seed until a token exists.** `config/upcoming_news_seed.json` holds headlines and links found by web search on 2026-09-30, run through the same rules. A later Apify run adds to it (upsert on city, mode and link hash).

## Consequences

- Good: new projects reach the map by re-running two commands; every claim is checkable against a link; no new dependency.
- Bad: a headline is a weak claim (it can be stale or wrong), so the page says to check the article; rules miss phrasing they do not know and miss city names not in the config; a pin at the city centre cannot show a route or a station; Apify runs cost money and the actor's output shape can change (`normalise_items` fails closed on an item without a title and link).

## Alternatives considered

- **Scrape publishers directly** — many sites, each with its own terms and layout, none maintained by us.
- **An LLM to read articles** — better recall, but a provider, cost and a review burden that ADR-0008 says to earn with a gold set first.
- **Wait for OSM `proposed=subway` ways** — lag of months, and buses are not mapped that way.

## Revisit when

The rejects file shows rules losing more real projects than they keep, a site's terms forbid the stored headline, or route geometry for upcoming lines becomes available from an official source.
