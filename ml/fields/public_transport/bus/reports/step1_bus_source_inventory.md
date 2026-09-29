# Step 1: Bus Data Source Inventory

## A. Sources discovered
1. **Delhi Open Transit Data (OTD)**: Static GTFS (stops, routes, schedules).
2. **TGSRTC Telangana GTFS (OpenCity)**: Static GTFS containing stops, routes, and schedules for TGSRTC buses in Telangana.
3. **TGSRTC Hyderabad Bus Stops (OpenCity)**: CSV extract of the stops for Hyderabad.
4. **Smart Cities Bus Fleet Data (MoHUA/OpenCity)**: CSV containing city-level bus fleets, terminals, and stops counts for smart cities (2015-18).
5. **OpenStreetMap India (Geofabrik)**: Contains geographic infrastructure layers (bus stops, bus stations). Already registered as `osm_india`.
6. **OGD India SRTU Fleet (MoRTH/dataful.in)**: State Road Transport Undertaking performance and fleet data.
7. **OGD India VAHAN Dashboard / ICED**: High-level statistical summaries.

## B. Sources accepted
1. `bus_tgsrtc_gtfs`: Direct OpenCity ZIP. Excellent structure, GTFS compliant.
2. `bus_tgsrtc_stops_csv`: Direct OpenCity CSV. Clean coordinates.
3. `bus_smartcities_fleet_csv`: Direct OpenCity CSV. Usable for city-level aggregate comparisons.
4. `osm_india`: Supplemented `used_by: [bus]`.

## C. Sources rejected
1. **OGD India SRTU Fleet (MoRTH / data.gov.in API)**: The data.gov.in APIs returned timeouts or 403 Forbidden errors when attempting to query the endpoints. Better left for offline PDF/manual ingestion if needed.
2. **OGD India VAHAN Dashboard**: Only offers high-level dashboards, no direct machine-readable granular bus endpoints available without authentication or scraping.

## D. Manual/API-key sources
1. **Delhi Open Transit Data (OTD)**: The `otd.delhi.gov.in` download requires a form submission (Name, Email, Purpose) protected by a CSRF token. It cannot be downloaded automatically with a simple GET request. It is marked as `MANUAL_DOWNLOAD_REQUIRED`.

## E. Geographic coverage
- Telangana (TGSRTC GTFS, Hyd Stops)
- Smart Cities (~37 cities nationwide)
- India-wide (OSM)

## F. Dataset type
- ZIP (GTFS specification)
- CSV
- PBF (OSM)

## G. Important fields
- GTFS: `stop_lat`, `stop_lon`, `route_id`, `stop_id`, `trip_id`, `departure_time`
- Smart Cities Fleet: `City Name`, `No. of buses`, `No. of bus stops`
- Hyd Stops: `stop_name`, `stop_lat`, `stop_lon`

## H. Official source / provider
- TGSRTC (Telangana State Road Transport Corporation)
- MoHUA (Ministry of Housing and Urban Affairs - Smart Cities Mission)
- Delhi OTD (Govt of NCT of Delhi)
- OpenStreetMap contributors

## I. Download status
All accepted sources successfully fetched via `ml/common/fetch.py`. Files exist in `data/raw/bus/`.

## J. Manifest status
Manifests generated successfully and SHA256 checksums recorded in `data/manifests/`.

## K. Data-quality observations
- TGSRTC GTFS is well-formed. It contains all 5 required GTFS files.
- Referential integrity for TGSRTC is perfect: `routes -> trips`, `trips -> stop_times`, and `stop_times -> stops` are fully intact.
- The Smart Cities CSV only has 74 rows, representing a subset of cities (e.g., Agartala), split by AC/Non-AC. It is an aggregate dataset, not a geospatial one.

## L. Recommended next step
**STEP 1 COMPLETE → READY FOR BUS DATA CLEANING + EDA**
