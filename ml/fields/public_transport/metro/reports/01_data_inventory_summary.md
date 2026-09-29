# Metro Data Inventory Summary

**Generated**: 2026-09-29  
**Status**: COMPLETE

## Overview

This inventory documents all Metro rail datasets collected for three Indian cities: Hyderabad, Bengaluru, and Chennai.

**Total Datasets**: 13  
**Cities Covered**: 3 (Hyderabad, Bengaluru, Chennai)  
**Data Sources**: OpenCity.in  
**Total Raw Data Size**: ~3.0 MB

## City Coverage Summary

### 1. Hyderabad (HMRL - Hyderabad Metro Rail Limited)

**Data Level**: NETWORK_LEVEL (Complete GTFS feed)  
**Data Richness**: HIGHEST

**Datasets**: 10 GTFS components

| Dataset | Rows | Columns | Key Information |
|---------|------|---------|-----------------|
| agency | 1 | 8 | Operator metadata |
| stops | 705 | 8 | Station locations with coordinates |
| routes | 3 | 8 | 3 Metro corridors (RED, GREEN, BLUE) |
| trips | 2,820 | 7 | Individual trip schedules |
| stop_times | 61,236 | 7 | Complete schedule data |
| calendar | 3 | 10 | Service patterns (weekday/Saturday/Sunday) |
| shapes | 2,450 | 5 | Route geometry (LineString points) |
| fare_attributes | 10 | 6 | Fare structure (₹12 to ₹60) |
| fare_rules | 3,249 | 3 | Origin-destination fare matrix |
| feed_info | 1 | 6 | Feed metadata and validity dates |

**Temporal Coverage**: 2026-07-03 to 2030-01-01  
**Coordinate System**: WGS84 (latitude/longitude)  
**Attribution**: "Contains data provided by Hyderabad Metro Rail Ltd."

**Capabilities**:
- ✓ Station-level analysis
- ✓ Route/network analysis
- ✓ Schedule frequency analysis
- ✓ Fare structure analysis
- ✓ Corridor geometry mapping
- ✓ Service pattern analysis

**Data Quality**:
- Missing data: 20.89% in stops.txt (mainly parent_station and platform_code fields)
- No duplicate records detected
- All GTFS files present and parseable

---

### 2. Bengaluru (BMRCL - Bangalore Metro Rail Corporation Limited)

**Data Level**: STATION_LEVEL  
**Data Richness**: MEDIUM

**Datasets**: 2

| Dataset | Rows | Columns | Key Information |
|---------|------|---------|-----------------|
| metro_stations_kml | 63 | 15 | Station locations, names (English + Kannada), colors |
| station_ridership | 95 | 2 | Station codes and names ONLY |

**Temporal Coverage**: None (snapshot data)  
**Coordinate System**: WGS84 (from KML)  
**Attribution**: "BMRCL (Bangalore Metro Rail Corporation Limited), via OpenCity.in"

**Capabilities**:
- ✓ Station-level spatial analysis
- ✓ Station accessibility analysis
- ✗ NO route geometry
- ✗ NO schedule data
- ✗ NO ridership values (despite filename!)

**CRITICAL LIMITATION**:
The file `bmrcl_station_ridership.csv` contains ONLY station codes and names. Despite its name, it contains NO ridership values, NO temporal data, and NO usage statistics. This is a station reference list, not ridership data.

**Data Quality**:
- KML: 63 stations with complete coordinates
- Station list: 95 station codes (includes some duplicates with alternate names)
- No missing values in available fields
- Coordinate quality requires validation

---

### 3. Chennai (CMRL - Chennai Metro Rail Limited)

**Data Level**: CITY_LEVEL (System-wide ridership)  
**Data Richness**: LOW

**Datasets**: 1

| Dataset | Rows | Columns | Key Information |
|---------|------|---------|-----------------|
| monthly_ridership | 39 | 8 | Monthly system-wide ridership by ticket type |

**Temporal Coverage**: April 2023 to June 2026 (39 months)  
**Ridership Fields**:
- Closed Loop (legacy smart cards)
- QR Tickets
- NCMC (National Common Mobility Card)
- Total Passenger Flow

**Attribution**: "CMRL (Chennai Metro Rail Limited), via OpenCity.in"

**Capabilities**:
- ✓ System-wide temporal trend analysis
- ✓ Ticket type adoption analysis
- ✗ NO station-level data
- ✗ NO route data
- ✗ NO coordinates
- ✗ NO spatial analysis possible

**Data Quality**:
- Complete monthly series (no gaps)
- No missing values
- Indian number formatting with commas (requires cleaning)
- Percentages stored as text with % symbols

---

## Data Comparability

### ⚠️ CRITICAL: These datasets are NOT directly comparable

| Metric | Hyderabad | Bengaluru | Chennai |
|--------|-----------|-----------|---------|
| Network geometry | ✓ Complete | ✗ Missing | ✗ Missing |
| Station locations | ✓ Complete | ✓ Complete | ✗ Missing |
| Schedules | ✓ Complete | ✗ Missing | ✗ Missing |
| Ridership | ✗ Missing | ✗ Missing | ✓ System-wide only |
| Fare structure | ✓ Complete | ✗ Missing | ✗ Missing |

**Consequence**: Cross-city comparisons must be limited to metrics supported by ALL cities. Network-level comparisons cannot include Chennai. Station-level accessibility cannot include Chennai.

---

## Known Data Issues

### Hyderabad GTFS
1. **Missing values** in stops.txt:
   - `parent_station`: 57% missing (expected for parent stations)
   - `platform_code`: Partially missing
2. **GTFS date**: Feed dated July 2026 (future date relative to data collection)
3. **Requires validation**: Referential integrity across files

### Bengaluru
1. **Misleading filename**: `bmrcl_station_ridership.csv` contains NO ridership
2. **Station count discrepancy**: KML has 63 stations, station list has 95 codes
3. **Missing network geometry**: Cannot map routes/corridors
4. **No temporal dimension**: Cannot analyze trends

### Chennai
1. **Number formatting**: Indian comma notation (e.g., "43,77,813") requires parsing
2. **Percentage symbols**: Need removal for numeric analysis
3. **No spatial component**: Cannot perform any geographic analysis
4. **System-wide only**: Cannot analyze station-level patterns
5. **Ticket type transition**: Shows shift from Closed Loop → NCMC (important trend)

---

## Next Steps

### Phase 2: Data Dictionary
Document every field's semantics, units, and validation rules.

### Phase 3-7: Cleaning
- **Hyderabad**: Clean all GTFS files, validate referential integrity
- **Bengaluru**: Parse KML to tabular format, validate coordinates, clarify station list
- **Chennai**: Parse Indian number format, convert percentages, validate temporal continuity

### Phase 8: Common Schema
Create unified data model while respecting incompatible data levels.

---

## File Manifest

All raw data located at: `data/raw/metro/{city}/`

**Hyderabad** (10 files, 2.9 MB total):
- `telangana_opendata_gtfs_hmrl_03_july_2026.zip` (compressed)
- Extracted: agency.txt, stops.txt, routes.txt, trips.txt, stop_times.txt, calendar.txt, shapes.txt, fare_attributes.txt, fare_rules.txt, feed_info.txt

**Bengaluru** (2 files, 82 KB total):
- `bengaluru_metro_stations.kml` (79 KB)
- `bmrcl_station_ridership.csv` (2 KB)

**Chennai** (1 file, 3 KB total):
- `cmrl_metro_ridership_2023_26.csv` (3 KB)

---

## Data Provenance

**Source**: OpenCity.in (India Open Data portal)  
**Downloaded**: 2026-09-29  
**License**: Terms of use on data.opencity.in — attribution required  
**Fetcher**: `ml/common/fetch.py`

**Attribution Requirements**:
- Hyderabad: "Contains data provided by Hyderabad Metro Rail Ltd."
- Bengaluru: "BMRCL (Bangalore Metro Rail Corporation Limited), via OpenCity.in"
- Chennai: "CMRL (Chennai Metro Rail Limited), via OpenCity.in"

---

## Inventory Artifact

**Machine-readable inventory**: `ml/fields/public_transport/metro/data/processed/metro_data_inventory.csv`

Contains complete metadata including:
- Dataset identifiers
- File paths and sizes
- Row/column counts
- Column names
- Missing value percentages
- Duplicate record percentages
- Coordinate availability
- Geometry type
- Primary key candidates
- Detailed notes
