# Bus Geospatial Report

## 1. Geographic Coverage
- Primary dataset: TGSRTC GTFS (Telangana / Hyderabad region)
- Independent stops: TGSRTC Hyderabad CSV
- Smart Cities fleet: 37 cities natively, but aggregate counts only (no point data).

## 2. Stop Geometries
- **Total mapped stops**: 5,028
- **Output file**: `bus_stops.geojson`
- **Missing/Invalid coordinates**: 0 (all stops possessed valid lat/lon between expected bounds).

## 3. Route Geometries
- **Status**: Derived from sequential stop times.
- **Reason**: The provided TGSRTC GTFS feed does NOT contain a `shapes.txt` file representing actual route geometry.
- **Methodology**: The longest/most representative trip for each of the 1,031 routes was selected, and its sequential stops were converted into a LineString.
- **Output file**: `bus_routes.geojson`
- **Total derived routes**: 1,031

## 4. LGD Geographic Joining
- **Status**: Skipped / Mocked
- **Reason**: The shared Geography data layers (`states`, `districts`, `subdistricts`, `ulbs`, `wards`) exist only as tabular mappings (`.csv`) without corresponding geospatial polygons/multipolygons (`.geojson` or `.shp`) in the `geography/data/processed/` directory.
- **Output**: `bus_stops_lgd_mapping.csv` and `bus_route_lgd_mapping.csv` have been generated with empty LGD codes/names pending the availability of geographic boundaries.
- **Unmatched stops**: 5,028 (all stops are unmatched due to missing boundary data).

## 5. Coverage Metrics
- Since population datasets and geographic bounds are missing, derived metrics such as "bus stops per sq km" or "bus stops per 100,000 population" could not be calculated.
- These descriptive coverage metrics are deferred to the final integration phase.
