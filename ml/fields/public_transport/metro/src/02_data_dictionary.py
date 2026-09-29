"""Generate comprehensive Metro data dictionary.

Documents every field across all datasets with semantics, data types, units,
validation rules, and cleaning actions.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
REPORTS = ROOT / "ml" / "fields" / "public_transport" / "metro" / "reports"


def create_data_dictionary() -> None:
    """Create comprehensive data dictionary markdown."""
    
    dictionary = """# Metro Data Dictionary

**Generated**: 2026-09-29  
**Version**: 1.0

This document defines every field across all Metro datasets, following actual GTFS semantics
and observed data characteristics.

---

## Hyderabad GTFS Fields

### agency.txt

| Field | Type | Meaning | Unit | Nullable | Source | Validation |
|-------|------|---------|------|----------|--------|------------|
| agency_id | TEXT | Unique agency identifier | - | No | GTFS spec | Non-empty string |
| agency_name | TEXT | Full agency name | - | No | GTFS spec | Non-empty string |
| agency_url | URL | Agency website | - | No | GTFS spec | Valid URL format |
| agency_timezone | TEXT | Timezone identifier | IANA TZ | No | GTFS spec | Valid timezone (Asia/Kolkata) |
| agency_lang | TEXT | Primary language | ISO 639-1 | No | GTFS spec | 2-letter code (en) |
| agency_fare_url | URL | Fare information URL | - | Yes | GTFS spec | Valid URL or empty |
| agency_email | EMAIL | Contact email | - | Yes | GTFS spec | Valid email format |
| agency_phone | TEXT | Contact phone | - | Yes | GTFS spec | Phone format with country code |

**Cleaning**: Validate URLs, phone format, email format.

---

### stops.txt

| Field | Type | Meaning | Unit | Nullable | Source | Validation |
|-------|------|---------|------|----------|--------|------------|
| stop_id | TEXT | Unique stop identifier | - | No | GTFS spec | Non-empty, unique |
| stop_name | TEXT | Station/platform name | - | No | GTFS spec | Non-empty string |
| stop_lat | DECIMAL | Latitude | Degrees | No | GTFS spec | [-90, 90], WGS84 |
| stop_lon | DECIMAL | Longitude | Degrees | No | GTFS spec | [-180, 180], WGS84 |
| zone_id | TEXT | Fare zone identifier | - | Yes | GTFS spec | References zone in fare_rules |
| location_type | INTEGER | Stop type (0=platform, 1=station) | - | Yes | GTFS spec | 0 or 1 |
| parent_station | TEXT | Parent station ID (for platforms) | - | Yes | GTFS spec | References stop_id where location_type=1 |
| platform_code | TEXT | Platform identifier (e.g., "1", "2") | - | Yes | GTFS spec | Short string |

**Key Semantics**:
- `location_type=1`: Parent station (has coordinates, no platform)
- `location_type=0`: Platform (has parent_station reference, has platform_code)
- Platforms share coordinates with parent station in this dataset

**Cleaning**: Validate coordinate ranges, check location_type consistency, validate parent_station references.

---

### routes.txt

| Field | Type | Meaning | Unit | Nullable | Source | Validation |
|-------|------|---------|------|----------|--------|------------|
| route_id | TEXT | Unique route identifier | - | No | GTFS spec | Non-empty, unique (RED/GREEN/BLUE) |
| agency_id | TEXT | Operating agency | - | No | GTFS spec | References agency.agency_id |
| route_short_name | TEXT | Short route name (e.g., "C1_RED") | - | No | GTFS spec | Non-empty string |
| route_long_name | TEXT | Full route description | - | No | GTFS spec | Includes terminal stations |
| route_type | INTEGER | Transit mode (1=Metro/Subway) | - | No | GTFS spec | Must be 1 for metro |
| route_color | HEX | Route color | 6-digit hex | Yes | GTFS spec | Valid hex without # |
| route_text_color | HEX | Text color on route | 6-digit hex | Yes | GTFS spec | Valid hex without # |
| route_sort_order | INTEGER | Display sort order | - | Yes | GTFS spec | Positive integer |

**Cleaning**: Validate agency_id references, verify route_type=1, validate hex colors.

---

### trips.txt

| Field | Type | Meaning | Unit | Nullable | Source | Validation |
|-------|------|---------|------|----------|--------|------------|
| service_id | TEXT | Service pattern (WK/SA/SU) | - | No | GTFS spec | References calendar.service_id |
| route_id | TEXT | Route identifier | - | No | GTFS spec | References routes.route_id |
| trip_id | TEXT | Unique trip identifier | - | No | GTFS spec | Non-empty, unique |
| direction_id | INTEGER | Direction (0/1) | - | Yes | GTFS spec | 0 or 1 |
| trip_headsign | TEXT | Destination shown to riders | - | Yes | GTFS spec | Station name |
| block_id | TEXT | Block identifier (vehicle run) | - | Yes | GTFS spec | String |
| shape_id | TEXT | Route geometry | - | Yes | GTFS spec | References shapes.shape_id |

**Cleaning**: Validate foreign key references, check direction_id values.

---

### stop_times.txt

| Field | Type | Meaning | Unit | Nullable | Source | Validation |
|-------|------|---------|------|----------|--------|------------|
| trip_id | TEXT | Trip identifier | - | No | GTFS spec | References trips.trip_id |
| stop_sequence | INTEGER | Stop order in trip (1, 2, 3...) | - | No | GTFS spec | Positive, sequential |
| stop_id | TEXT | Stop/platform identifier | - | No | GTFS spec | References stops.stop_id |
| arrival_time | TIME | Arrival time | HH:MM:SS | No | GTFS spec | Valid time, may exceed 24:00:00 |
| departure_time | TIME | Departure time | HH:MM:SS | No | GTFS spec | >= arrival_time |
| timepoint | INTEGER | Exact time (1) or approximate (0) | - | Yes | GTFS spec | 0 or 1 |
| shape_dist_traveled | DECIMAL | Distance from start | Meters | Yes | GTFS spec | Monotonically increasing |

**Key Semantics**:
- Times may exceed 24:00:00 for trips after midnight (e.g., 25:30:00)
- `stop_sequence` must be unique within a trip
- `shape_dist_traveled` cumulative distance along route

**Cleaning**: Validate time format, ensure departure >= arrival, check sequence ordering.

---

### calendar.txt

| Field | Type | Meaning | Unit | Nullable | Source | Validation |
|-------|------|---------|------|----------|--------|------------|
| service_id | TEXT | Service pattern identifier | - | No | GTFS spec | Unique (WK/SA/SU) |
| monday | BOOLEAN | Operates on Mondays | - | No | GTFS spec | 0 or 1 |
| tuesday | BOOLEAN | Operates on Tuesdays | - | No | GTFS spec | 0 or 1 |
| wednesday | BOOLEAN | Operates on Wednesdays | - | No | GTFS spec | 0 or 1 |
| thursday | BOOLEAN | Operates on Thursdays | - | No | GTFS spec | 0 or 1 |
| friday | BOOLEAN | Operates on Fridays | - | No | GTFS spec | 0 or 1 |
| saturday | BOOLEAN | Operates on Saturdays | - | No | GTFS spec | 0 or 1 |
| sunday | BOOLEAN | Operates on Sundays | - | No | GTFS spec | 0 or 1 |
| start_date | DATE | Service start | YYYYMMDD | No | GTFS spec | Valid date |
| end_date | DATE | Service end | YYYYMMDD | No | GTFS spec | Valid date >= start_date |

**Service Patterns Observed**:
- `WK`: Weekday service (Mon-Fri)
- `SA`: Saturday service
- `SU`: Sunday service

**Cleaning**: Validate date formats, ensure at least one day=1 per service.

---

### shapes.txt

| Field | Type | Meaning | Unit | Nullable | Source | Validation |
|-------|------|---------|------|----------|--------|------------|
| shape_id | TEXT | Shape identifier | - | No | GTFS spec | References trips.shape_id |
| shape_pt_lat | DECIMAL | Point latitude | Degrees | No | GTFS spec | [-90, 90], WGS84 |
| shape_pt_lon | DECIMAL | Point longitude | Degrees | No | GTFS spec | [-180, 180], WGS84 |
| shape_pt_sequence | INTEGER | Point order (1, 2, 3...) | - | No | GTFS spec | Positive, sequential per shape_id |
| shape_dist_traveled | DECIMAL | Distance from start | Meters | Yes | GTFS spec | Monotonically increasing |

**Key Semantics**:
- Ordered points form LineString geometry for route visualization
- `shape_dist_traveled` matches values in stop_times.txt
- Multiple shapes may exist per route (for different directions/variants)

**Cleaning**: Validate coordinates, check sequence ordering, verify distance monotonicity.

---

### fare_attributes.txt

| Field | Type | Meaning | Unit | Nullable | Source | Validation |
|-------|------|---------|------|----------|--------|------------|
| fare_id | TEXT | Fare identifier | - | No | GTFS spec | Unique (F_12, F_18, ...) |
| price | DECIMAL | Fare amount | Currency | No | GTFS spec | Non-negative |
| currency_type | TEXT | Currency code | ISO 4217 | No | GTFS spec | "INR" for Indian Rupee |
| payment_method | INTEGER | Payment timing | - | No | GTFS spec | 0=on-board, 1=before |
| transfers | INTEGER | Transfers allowed | - | Yes | GTFS spec | Empty for metro |
| agency_id | TEXT | Applicable agency | - | Yes | GTFS spec | References agency.agency_id |

**Observed Fares**: ₹12, ₹18, ₹30, ₹40, ₹50, ₹60 (distance-based)

**Cleaning**: Validate currency code, ensure price > 0.

---

### fare_rules.txt

| Field | Type | Meaning | Unit | Nullable | Source | Validation |
|-------|------|---------|------|----------|--------|------------|
| origin_id | TEXT | Origin zone | - | No | GTFS spec | References stops.zone_id |
| destination_id | TEXT | Destination zone | - | No | GTFS spec | References stops.zone_id |
| fare_id | TEXT | Applicable fare | - | No | GTFS spec | References fare_attributes.fare_id |

**Key Semantics**:
- Origin-destination fare matrix
- 3,249 combinations covering all station pairs
- Same origin-destination = minimum fare

**Cleaning**: Validate all foreign key references.

---

### feed_info.txt

| Field | Type | Meaning | Unit | Nullable | Source | Validation |
|-------|------|---------|------|----------|--------|------------|
| feed_publisher_name | TEXT | Publisher name | - | No | GTFS spec | "Open Data Telangana" |
| feed_publisher_url | URL | Publisher URL | - | No | GTFS spec | Valid URL |
| feed_lang | TEXT | Feed language | ISO 639-1 | No | GTFS spec | 2-letter code |
| feed_contact_url | URL | Contact URL | - | Yes | GTFS spec | Valid URL |
| feed_start_date | DATE | Feed validity start | YYYYMMDD | Yes | GTFS spec | 20260703 |
| feed_end_date | DATE | Feed validity end | YYYYMMDD | Yes | GTFS spec | 20300101 |

**Cleaning**: Validate URLs and dates.

---

## Bengaluru Fields

### bengaluru_metro_stations.kml

Extracted from KML `<Placemark>` and `<ExtendedData>` elements.

| Field | Type | Meaning | Unit | Nullable | Source | Validation |
|-------|------|---------|------|----------|--------|------------|
| name | TEXT | Station name (English) | - | No | KML | Non-empty string |
| coordinates | POINT | Station location | Lon, Lat | No | KML | Valid WGS84 coordinates |
| @id | TEXT | OSM node ID | - | Yes | Extended | Format: "node/[number]" |
| colour | HEX | Line color | Hex with # | Yes | Extended | Valid hex color |
| name:kn | TEXT | Station name (Kannada) | - | Yes | Extended | Kannada script |
| network | TEXT | Network name | - | Yes | Extended | "Namma Metro" |
| old_name | TEXT | Previous station name | - | Yes | Extended | String |
| operator | TEXT | Operating agency | - | Yes | Extended | "BMRCL" |
| public_transport | TEXT | Type indicator | - | Yes | Extended | "stop_position" |
| railway | TEXT | Railway type | - | Yes | Extended | "station" |
| station | TEXT | Station type | - | Yes | Extended | "subway" |
| subway | TEXT | Subway indicator | - | Yes | Extended | "yes" |
| wheelchair | TEXT | Accessibility | - | Yes | Extended | "yes"/"no"/"limited" |
| wikipedia | TEXT | Wikipedia reference | - | Yes | Extended | Language:Article |

**Cleaning**: Parse KML XML, extract coordinates from `<Point>` geometry, extract extended data.

---

### bmrcl_station_ridership.csv

**⚠️ CRITICAL**: Despite filename, this file contains NO ridership data.

| Field | Type | Meaning | Unit | Nullable | Source | Validation |
|-------|------|---------|------|----------|--------|------------|
| code | TEXT | Station code | - | No | CSV | 4-letter code, unique |
| name | TEXT | Station name | - | No | CSV | Non-empty string |

**Actual Content**: Station reference list with 95 station codes and names.  
**Missing**: Ridership values, temporal data, passenger counts.

**Cleaning**: Verify uniqueness, cross-reference with KML station names.

---

## Chennai Fields

### cmrl_metro_ridership_2023_26.csv

| Field | Type | Meaning | Unit | Nullable | Source | Validation |
|-------|------|---------|------|----------|--------|------------|
| Month | TEXT | Month-Year | Mon-YY | No | CSV | Format: "Apr-23" |
| Closed Loop (Ridership) | TEXT | Closed loop ridership | Passengers | No | CSV | Indian comma format |
| Closed Loop % | TEXT | Closed loop percentage | Percent | No | CSV | Format: "65.15%" |
| QR Tickets (Ridership) | TEXT | QR ticket ridership | Passengers | No | CSV | Indian comma format |
| QR % | TEXT | QR percentage | Percent | No | CSV | Format: "34.82%" |
| NCMC (Ridership) | TEXT | NCMC ridership | Passengers | No | CSV | Indian comma format |
| NCMC % | TEXT | NCMC percentage | Percent | No | CSV | Format: "0.03%" |
| Total Passenger Flow | TEXT | Total ridership | Passengers | No | CSV | Indian comma format |

**Key Semantics**:
- **Closed Loop**: Legacy CMRL smart cards (being phased out)
- **QR Tickets**: Single-journey QR code tickets
- **NCMC**: National Common Mobility Card (RuPay-based, growing adoption)

**Temporal Trend**: Clear shift from Closed Loop → NCMC (0.03% in Apr-23 to 51.43% in Dec-25)

**Number Format**: Indian notation with commas
- Example: "43,77,813" means 437,7813 = 4,377,813 passengers
- Pattern: Groups of 2 digits from right, then groups of 3: XX,XX,XXX

**Cleaning Actions**:
1. Parse month-year to proper date (first day of month)
2. Remove commas from ridership fields, convert to integer
3. Remove % symbols, convert to float
4. Validate percentages sum to ~100% (±rounding)
5. Validate Total = sum of three ticket types

**Validation Rules**:
- Month field must parse correctly
- Ridership values must be positive integers
- Percentages must be 0-100
- Sum of percentages should be 99-101% (allowing rounding)
- Total should equal sum of components (±1 for rounding)

---

## Coordinate Systems

All spatial data uses **WGS84 (EPSG:4326)**:
- Latitude: -90 to +90 degrees
- Longitude: -180 to +180 degrees
- India typical range: Lat 8°-36°N, Lon 68°-97°E

**City Coordinate Ranges** (for validation):
- Hyderabad: ~17.3-17.5°N, 78.3-78.6°E
- Bengaluru: ~12.8-13.2°N, 77.4-77.8°E
- Chennai: ~12.9-13.3°N, 80.1-80.3°E

---

## Data Type Conventions

| Convention | Meaning | Example |
|------------|---------|---------|
| TEXT | String, variable length | "Miyapur" |
| INTEGER | Whole number | 705 |
| DECIMAL | Floating point | 17.4965452 |
| BOOLEAN | Binary flag | 0 or 1 |
| DATE | Date without time | 20260703 |
| TIME | Time in 24h | 06:01:06 |
| URL | Web address | https://... |
| EMAIL | Email address | user@domain.com |
| HEX | Hexadecimal color | E31E24 |
| POINT | Geographic point | (78.373, 17.496) |

---

## Validation Priority

**CRITICAL** (must pass):
- Primary key uniqueness
- Foreign key integrity
- Coordinate ranges
- Required fields non-null

**HIGH** (should pass):
- Data type correctness
- Format compliance
- Logical consistency

**MEDIUM** (nice to have):
- No duplicate records
- Complete optional fields
- Standard formatting

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-09-29 | Initial data dictionary based on actual file inspection |

---

**Next**: Phase 3-7 cleaning scripts will implement these validation rules.
"""
    
    REPORTS.mkdir(parents=True, exist_ok=True)
    output_path = REPORTS / "02_metro_data_dictionary.md"
    output_path.write_text(dictionary)
    
    print(f"✓ Metro data dictionary created: {output_path.relative_to(ROOT)}")
    print("  Documented: 10 GTFS files, 2 Bengaluru files, 1 Chennai file")
    print("  Total fields documented: ~80 fields with complete semantics")


if __name__ == "__main__":
    create_data_dictionary()
