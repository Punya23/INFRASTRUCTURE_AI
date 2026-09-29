# Public transport — GTFS integration

Every GTFS feed goes through the same path as the NH and toll sources:

1. It is registered in `config/sources.yaml`, with community repos pinned to a commit.
2. It is fetched with a manifest (`data/manifests/<id>.yaml`: sha256, fetched_at).
3. It is validated. Structural problems reject the whole feed, and row problems are counted in `reports/feed_issues.csv`.
4. It is stored with provenance: `source`, `source_ref`, `fetched_at`, `license`, `confidence`, `tier`.
5. It is linked to the NH network and toll plazas.
6. It is exported as contract fixtures.

```bash
cd ml && uv run python -m common.fetch <feed ids from config/fields/public_transport.yaml>
cd ml && uv run python -m fields.public_transport.gtfs all      # feeds → link → fixtures
```

Feeds, their mode, operator and tier, and every threshold live in `config/fields/public_transport.yaml`. The reader and validator (`ml/pipeline/gtfs.py`) are shared and field-agnostic.

## Feeds (2026-09-29)

| Feed | Tier | Stops | Routes | Stops ≤ 1 km of an NH | Bus routes passing an NH toll plaza |
|---|---|---|---|---|---|
| TGSRTC bus, Hyderabad | official (OpenCity) | 5,028 | 1,031 | 32% | 246 (15 plazas) |
| HMRL metro, Hyderabad | official (OpenCity) | 705 | 3 | 50% | — |
| BEST bus, Mumbai | secondary | 10,279 | 1,115 | 50% | 47 (6) |
| PMPML bus, Pune | secondary | 6,713 | 617 | 48% | 70 (12) |
| BMTC bus, Bengaluru | secondary | 9,960 | 4,416 | 34% | 1,011 (46) |
| MTC bus, Chennai | secondary | 5,580 | 3,934 | 27% | 225 (5) |
| CMRL metro, Chennai | secondary | 44 | 3 | 27% | — |
| BMRCL metro, Bengaluru | secondary | 488 | 3 | 57% | — |

Details are in `reports/feed_summary.csv`, `reports/nh_toll_link_by_feed.csv` and `reports/toll_plazas_on_transit_routes.csv`.

## Caveats

- **Secondary feeds are community-maintained**, not operator releases. They carry `tier: secondary` and confidence 0.7 on every row and fixture feature. Validate them against official data before citing any number.
- **Routes listed without trips have no geometry.** These are counted as `route_no_geometry` in `reports/feed_issues.csv`: BEST 494, MTC 677, BMTC 18.
- **Some feeds ship no shapes.** Where `shapes.txt` is missing (BEST, MTC, TGSRTC), route lines join the stops of each route's longest trip. That is straight stop-to-stop, not the road path.
- **The toll link is spatial proximity**: a bus route within 150 m of an OSM toll plaza. A route running at grade under an elevated tolled road also counts, so treat these as upper bounds, not confirmed toll crossings. Metro lines are excluded.
- **Licenses:** BEST and PMPML are MIT-0, MTC and CMRL are MIT, and BMTC and BMRCL are ODbL-1.0. Anything exported from the BMTC or BMRCL fixtures must stay ODbL (share-alike) and attribute the repo.
- **Not integrated:** `justjkk/chennai-rail-gtfs` has no license, was last updated in 2011, and ships no feed zip.
- **Blocked:** Delhi DTC and DMRC (otd.delhi.gov.in) need a manual browser download because of CSRF protection. Once someone saves them to `data/raw/`, register them with a manifest and add them to the config.
