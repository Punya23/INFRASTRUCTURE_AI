# Metro Data Quality Report

**Generated**: 2026-09-29  
**Status**: COMPLETE

## Executive Summary

Successfully cleaned and validated Metro data for 3 Indian cities:
- **Hyderabad**: Complete GTFS network data (NETWORK_LEVEL)
- **Bengaluru**: Station locations (STATION_LEVEL)
- **Chennai**: Monthly ridership trends (CITY_LEVEL)

## Data Completeness

| City | Data Level | Stations | Network | Schedule | Ridership | Status |
|------|------------|----------|---------|----------|-----------|--------|
| Hyderabad | NETWORK_LEVEL | ✓ 57 | ✓ 3 routes | ✓ 2820 trips | ✗ | COMPLETE |
| Bengaluru | STATION_LEVEL | ✓ 63 | ✗ | ✗ | ✗ | PARTIAL |
| Chennai | CITY_LEVEL | ✗ | ✗ | ✗ | ✓ 39 months | PARTIAL |

## Cleaning Summary

### Hyderabad GTFS
- ✓ All 10 GTFS files cleaned
- ✓ Referential integrity validated (10/10 checks passed)
- ✓ Coordinate validation applied
- ✓ No orphan records
- ✓ Primary keys unique

### Bengaluru
- ✓ 63 stations extracted from KML
- ✓ Coordinates validated (Bengaluru bounding box)
- ✓ 91 station codes from reference list
- ⚠️ Station code list contains NO ridership data despite filename

### Chennai
- ✓ 39 months of ridership (Apr 2023 - Jun 2026)
- ✓ Indian number format parsed correctly
- ✓ Percentage validation passed
- ✓ Component sums match totals (±0 passengers)
- ✓ Shows ticket type transition: Closed Loop→NCMC

## Data Quality Metrics

### Missing Values
- Hyderabad GTFS: 20.89% (mostly optional platform_code, parent_station)
- Bengaluru KML: 0% (complete for available fields)
- Chennai Ridership: 0% (complete series)

### Duplicate Records
- All datasets: 0% after deduplication

### Coordinate Quality
- Hyderabad: 57 stations with validated coordinates
- Bengaluru: 63 stations with validated coordinates
- Chennai: No spatial data

## Key Statistics

| City | Metric | Value | Unit |
|------|--------|-------|------|
| Hyderabad | Total stations | 57 | stations |
| Hyderabad | Total platforms | 117 | platforms |
| Hyderabad | Routes/corridors | 3 | routes |
| Hyderabad | Total trips | 2820 | trips |
| Hyderabad | Stop times | 61236 | records |
| Hyderabad | Shape points | 2450 | points |
| Bengaluru | Total stations | 63 | stations |
| Chennai | Ridership months | 39 | months |
| Chennai | Total ridership (period) | 345333510 | passengers |
| Chennai | Average monthly ridership | 8854705 | passengers/month |
| Chennai | Peak monthly ridership | 10468732 | passengers/month |
 Data Limitations

### Hyderabad
- ✓ Network-complete
- ✗ No actual ridership data
- ✓ Can analyze: network topology, accessibility, service patterns, fares

### Bengaluru
- ✓ Station locations available
- ✗ No route geometry
- ✗ No schedules
- ✗ No ridership (despite misleading filename)
- ✓ Can analyze: station accessibility, spatial distribution

### Chennai
- ✓ System-wide ridership trends
- ✗ No station-level data
- ✗ No spatial data
- ✗ Cannot perform geographic analysis
- ✓ Can analyze: temporal trends, ticket adoption

## Comparability Warning

**CRITICAL**: These datasets represent different data levels and CANNOT be directly compared:

- Hyderabad = NETWORK_LEVEL
- Bengaluru = STATION_LEVEL
- Chennai = CITY_LEVEL

Any cross-city analysis must account for these fundamental differences.

## Next Steps

✓ Common data model created
✓ Geospatial exports generated
□ LGD mapping (requires boundary geometry)
□ Population integration (requires spatial data)
□ Accessibility analysis (requires boundaries + population)

## Reproducibility

All cleaning steps documented in:
- `ml/fields/public_transport/metro/src/03_clean_hyderabad_gtfs.py`
- `ml/fields/public_transport/metro/src/04_clean_bengaluru_chennai.py`
- `ml/fields/public_transport/metro/src/05_integrated_analysis.py`

Clean data location: `ml/fields/public_transport/metro/data/processed/`
