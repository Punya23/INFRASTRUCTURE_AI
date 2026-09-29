# Step 2: Bus Data Quality Report

## 1. TGSRTC GTFS

### Processed Files
- `agency_clean.csv`: 1 row, 5 columns. No missing agency IDs.
- `stops_clean.csv`: 5,028 rows, 7 columns.
- `routes_clean.csv`: 1,031 rows, 4 columns.
- `trips_clean.csv`: 44,892 rows, 5 columns.
- `stop_times_clean.csv`: 1,132,807 rows, 5 columns.
- `calendar_clean.csv`: 1 row, 10 columns.
- `feed_info_clean.csv`: 1 row, 6 columns.

### Missing Values & Duplicates
- **agency**: No missing values.
- **stops**: No missing coordinates. `valid_coords` flag created; all 5,028 stops have valid coordinates between -90/90 and -180/180. No missing `stop_id`.
- **routes**: No missing `route_id`.
- **trips**: No missing `trip_id`, `route_id`, or `service_id`.
- **stop_times**: No missing `trip_id`, `stop_id` or `stop_sequence`.
- **calendar**: No missing values.

### Referential Integrity
- **routes -> trips**: OK
- **trips -> stop_times**: OK
- **stop_times -> stops**: OK

### Cleaning Decisions
- Stripped whitespace from all object/string columns.
- Preserved existing GTFS schemas without changing IDs.
- Converted lat/lon to numeric types, keeping original precision.
- Validated referential relationships.

---

## 2. TGSRTC Stops CSV

### Overview
- `tgsrtc_stops_clean.csv`: 5,028 rows, 7 columns.

### Missing Values & Duplicates
- Contains identically 5,028 rows, matching the GTFS `stops.txt` completely.
- Duplicates: `stop_id` has 0 duplicates.
- Missing values: `stop_desc` is empty for many stops, which is normal.
- Coordinates: All 5,028 rows contain valid coordinates.

### Cleaning Decisions
- Stripped whitespace from string columns.
- Enforced numeric parsing for `stop_lat` and `stop_lon`.
- Flagged coordinates using `valid_coords` mask.

---

## 3. Smart Cities Bus Fleet (MoHUA)

### Overview
- `smartcities_bus_fleet_clean.csv`: 74 rows, 6 columns.

### Missing Values & Duplicates
- Contains aggregate data for ~37 cities (split by AC and Non AC).
- Missing values: Converted string '-' and 'nan' to proper null values.
- Columns `No. of buses of that type`, `No. of bus terminals`, `No. of bus stands`, and `No. of bus stops` converted from string (with commas) to integers/floats.

### Cleaning Decisions
- Cleaned string representations of numeric counts (removed commas, handled hyphens).
- Preserved the separation of AC and Non AC. 
- Represented missing numeric data natively as empty/NaN instead of '-' strings.
