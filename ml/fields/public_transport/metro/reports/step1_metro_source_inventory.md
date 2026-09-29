# Metro Step 1 — Source Inventory

## Summary

Systematic source discovery was performed for 14 target Metro systems across India.

Four sources with verified direct GET download URLs were registered and downloaded via the shared fetcher (`ml/common/fetch.py`). All others are documented below with their reason for not being downloadable automatically.

---

## Source Inventory Table

| Metro System | Operator | Source | Format | Official? | Stations | Routes | Trips | Stop Times | Shapes | Frequency | Ridership | Status |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **Hyderabad** | HMRL | OpenCity.in | GTFS ZIP | Yes | 705 | 3 | 2,820 | 61,236 | 6 shapes (2,450 pts) | N/A | N/A | ✅ DOWNLOADED |
| **Bengaluru** | BMRCL | OpenCity.in | KML | Yes | 63 | N/A | N/A | N/A | Lines in KML | N/A | N/A | ✅ DOWNLOADED |
| **Bengaluru** | BMRCL | OpenCity.in | CSV | Yes | N/A | N/A | N/A | N/A | N/A | N/A | 95 station codes | ✅ DOWNLOADED |
| **Chennai** | CMRL | OpenCity.in | CSV | Yes | N/A | N/A | N/A | N/A | N/A | N/A | 39 monthly records | ✅ DOWNLOADED |
| **Delhi** | DMRC | otd.delhi.gov.in | GTFS (form) | Yes | ~262 (claimed) | ~36 | ~17,997 | ~411,686 | Unknown | Unknown | N/A | ❌ MANUAL — CSRF form required |
| **Mumbai** | MMRDA/MML | No open-data portal found | — | — | — | — | — | — | — | — | — | ❌ NO USABLE SOURCE FOUND |
| **Pune** | Pune Metro | Only DPR documents on OpenCity | PDF | Yes | N/A | N/A | N/A | N/A | N/A | N/A | N/A | ❌ PDF ONLY (DPR) |
| **Nagpur** | Nagpur Metro | No machine-readable dataset found | — | — | — | — | — | — | — | — | — | ❌ NO USABLE SOURCE FOUND |
| **Ahmedabad** | MEGA | No open-data GTFS found | — | — | — | — | — | — | — | — | — | ❌ NO USABLE SOURCE FOUND |
| **Jaipur** | JMC/JMRC | No open-data GTFS found | — | — | — | — | — | — | — | — | — | ❌ NO USABLE SOURCE FOUND |
| **Kochi** | KMRL | No direct-download GTFS found | — | — | — | — | — | — | — | — | — | ❌ NO USABLE SOURCE FOUND |
| **Lucknow** | LMRC | No open-data dataset found | — | — | — | — | — | — | — | — | — | ❌ NO USABLE SOURCE FOUND |
| **Noida** | NMRC | Operated by DMRC; deferred under Delhi | — | — | — | — | — | — | — | — | — | ❌ DEFERRED (under Delhi) |
| **Gurugram Rapid** | RMGL | Ceased operations 2023 | — | — | — | — | — | — | — | — | — | ❌ DEFUNCT |
| **Kolkata** | KMRC | No open-data GTFS found | — | — | — | — | — | — | — | — | — | ❌ NO USABLE SOURCE FOUND |

---

## Downloaded Sources

### Source 1 — Hyderabad HMRL GTFS
- **Source ID**: `metro_hyd_hmrl_gtfs`
- **Raw file**: `data/raw/metro/hyderabad/telangana_opendata_gtfs_hmrl_03_july_2026.zip`
- **Manifest**: `data/manifests/metro_hyd_hmrl_gtfs.yaml`
- **Provider**: HMRL via OpenCity.in
- **Reference date**: 2026-07-03
- **GTFS files present**: agency, stops, routes, trips, stop_times, calendar, shapes, fare_attributes, fare_rules, feed_info
- **Stops**: 705 | **Routes**: 3 | **Trips**: 2,820 | **Stop times**: 61,236 | **Shapes**: 6 (2,450 points)
- **Shapes available**: YES (shapes.txt with 6 shapes covering 3 metro lines × 2 directions)
- **Frequency**: N/A (frequencies.txt absent)
- **Ridership**: NOT AVAILABLE in GTFS feed

### Source 2 — Bengaluru BMRCL Stations KML
- **Source ID**: `metro_bengaluru_stations_kml`
- **Raw file**: `data/raw/metro/bengaluru/bengaluru_metro_stations.kml`
- **Manifest**: `data/manifests/metro_bengaluru_stations_kml.yaml`
- **Provider**: BMRCL via OpenCity.in
- **Reference date**: 2024
- **Stations in KML**: 63 named placemarks with coordinates

### Source 3 — Bengaluru BMRCL Ridership CSV
- **Source ID**: `metro_bengaluru_bmrcl_ridership_csv`
- **Raw file**: `data/raw/metro/bengaluru/bmrcl_station_ridership.csv`
- **Manifest**: `data/manifests/metro_bengaluru_bmrcl_ridership_csv.yaml`
- **Provider**: BMRCL via OpenCity.in
- **Content**: 95 rows — station code and station name only (no ridership figures despite dataset title)
- **Note**: Dataset labelled "station-wise ridership" contains only station code→name lookup table.

### Source 4 — Chennai CMRL Ridership CSV
- **Source ID**: `metro_chennai_cmrl_ridership_csv`
- **Raw file**: `data/raw/metro/chennai/cmrl_metro_ridership_2023_26.csv`
- **Manifest**: `data/manifests/metro_chennai_cmrl_ridership_csv.yaml`
- **Provider**: CMRL via OpenCity.in
- **Content**: 39 monthly records (Apr 2023 – Jun 2026) with total passenger flow by ticket type
- **Ridership**: YES (official CMRL monthly ridership data)

---

## Unavailable Systems

| System | Reason | Evidence |
|---|---|---|
| Delhi (DMRC) | CSRF/form-gated download on otd.delhi.gov.in | HTTP 200 but page requires user form submission |
| Mumbai Metro | No machine-readable open-data portal located | Searched MMRDA, MCGM, MML portals — no GTFS/CSV endpoint |
| Pune Metro | Only detailed project report (PDF) on OpenCity | `bengaluru-metro-phase-*/documents` equivalent |
| Nagpur Metro | No open-data source found | MahaMetro website has no data download section |
| Ahmedabad (MEGA) | No GTFS or station data CSV found | MEGA portal has static HTML only |
| Jaipur Metro | No open-data found | Jaipur Metro Rail Corporation has no open-data section |
| Kochi (KMRL) | No direct-download GTFS found | KMRL website links to apps only |
| Lucknow (LMRC) | No open-data dataset | LMRC website is informational only |
| Noida (NMRC) | Incorporated into Delhi Metro operations | Deferred to Delhi |
| Gurugram Rapid Metro | Ceased operations in January 2023 | Not applicable |
| Kolkata (KMRC/East-West) | No machine-readable GTFS found | No OpenCity or OGD dataset available |

---

## Notes on Coverage Limitations

1. This Step 1 represents **3 metro systems** with machine-readable data (Hyderabad with full GTFS; Bengaluru with station geography + code reference; Chennai with ridership only).
2. Delhi Metro data **exists** but is behind a CSRF-protected form download wall on `otd.delhi.gov.in` — same gating mechanism as Delhi Bus OTD.
3. The Bengaluru KML and ridership CSV do NOT constitute a complete GTFS feed. No stop_times, trips or schedules are available for Bengaluru from open sources.
4. Chennai ridership CSV does NOT include station locations or network topology.
5. Only Hyderabad provides a complete GTFS feed suitable for full network analysis.
