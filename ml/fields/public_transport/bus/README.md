# LokDrishti AI — Bus Domain Pipeline

## 1. Purpose
This directory contains the data ingestion, cleaning, validation, exploratory data analysis (EDA), and geospatial processing pipeline for the Public Transport Bus domain within the LokDrishti AI project.

## 2. Sources
1. **TGSRTC GTFS**: Comprehensive static GTFS for Telangana / Hyderabad. (Verified)
2. **TGSRTC Hyderabad Stops**: Additional standalone CSV of bus stops. (Verified)
3. **Smart Cities Bus Fleet**: Aggregate metrics from MoHUA. (Verified)
4. **Delhi OTD GTFS**: Manual download required (CSRF/Form). (Deferred)
5. **OGD SRTU Fleet**: API access issues. (Deferred)
6. **OSM India**: Reused from shared layers.

## 3. Raw Data Locations
Raw datasets downloaded via `ml/common/fetch.py` are preserved intact at:
- `data/raw/bus/tgsrtc/telangana_opendata_gtfs_tgsrtc_08_february_2026.zip`
- `data/raw/bus/tgsrtc/hyd_stops.csv`
- `data/raw/bus/ogd/smartcities_bus_fleet.csv`

## 4. Processed Data Locations
Cleaned datasets and spatial data are stored in:
- `ml/fields/public_transport/bus/data/processed/`

Outputs include:
- `bus_agency_clean.csv`
- `bus_stops_clean.csv`
- `bus_routes_clean.csv`
- `bus_trips_clean.csv`
- `bus_stop_times_clean.csv`
- `bus_calendar_clean.csv`
- `bus_feed_info_clean.csv`
- `bus_tgsrtc_stops_clean.csv`
- `smartcities_bus_fleet_clean.csv`
- `bus_stops.geojson`
- `bus_routes.geojson`
- `bus_stops_lgd_mapping.csv`
- `bus_route_lgd_mapping.csv`
- `bus_spatial_summary.csv`

## 5. Cleaning Pipeline
The cleaning script standardizes datatypes, strips whitespace, converts lat/lon to floats, detects coordinate anomalies, handles null placeholders in OGD data, and outputs clean CSVs without overwriting original IDs.
Script: `ml/fields/public_transport/bus/src/clean_bus_data.py`

## 6. Validation
The validation script checks for existence of processed files, verifies file sizes, and checks relational referential integrity mapping across the GTFS dataset.
Script: `ml/fields/public_transport/bus/src/validate_bus.py`

## 7. EDA
Jupyter notebooks for descriptive analysis and basic visualization:
- `ml/fields/public_transport/bus/notebooks/01_bus_eda.ipynb` (Created from generation script)

## 8. Geospatial Analysis
The geospatial pipeline maps stops to GeoJSON Points and derives route geometries from stop times (since shapes.txt is missing). LGD joins are mocked pending the arrival of spatial boundary polygons in the core geography module.
Script: `ml/fields/public_transport/bus/src/geospatial_bus.py`

## 9. Known Limitations
- No ridership data exists in the current feeds.
- LGD Geospatial join cannot be completed yet due to missing geometry in `ml/fields/geography`.
- Route shapes are derived from point-to-point stop segments rather than precise road alignments.
- Delhi GTFS requires manual UI download due to CSRF protection.

## 10. How to Reproduce
Run from the root `INFRASTRUCTURE_AI` directory:
```bash
# 1. Download data (Requires setup from config/sources.yaml)
uv run python -m common.fetch bus_tgsrtc_gtfs bus_tgsrtc_stops_csv bus_smartcities_fleet_csv

# 2. Clean data
uv run python ml/fields/public_transport/bus/src/clean_bus_data.py

# 3. Rename processed to match naming convention (if needed)
cd ml/fields/public_transport/bus/data/processed/
for f in agency_clean.csv calendar_clean.csv feed_info_clean.csv routes_clean.csv stop_times_clean.csv stops_clean.csv tgsrtc_stops_clean.csv trips_clean.csv; do mv $f bus_$f; done
cd ../../../../../../

# 4. Generate Geospatial Data
uv run python ml/fields/public_transport/bus/src/geospatial_bus.py

# 5. Generate Notebooks
uv run python ml/fields/public_transport/bus/src/generate_notebooks.py

# 6. Validate
uv run python ml/fields/public_transport/bus/src/validate_bus.py
```
