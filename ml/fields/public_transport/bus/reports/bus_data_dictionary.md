# Step 3: Bus Data Dictionary

## 1. TGSRTC GTFS

### `bus_agency_clean.csv`
- `agency_id` (string) [SOURCE]: Unique identifier for the agency.
- `agency_name` (string) [SOURCE]: Full name of the transit agency.
- `agency_url` (string) [SOURCE]: Website of the agency.
- `agency_timezone` (string) [SOURCE]: Timezone in which the agency operates.
- `agency_lang` (string) [SOURCE]: Primary language used by the agency.

### `bus_stops_clean.csv`
- `stop_id` (string) [SOURCE, PRIMARY KEY]: Unique identifier for the stop.
- `stop_name` (string) [SOURCE]: Name of the stop.
- `stop_lat` (float) [SOURCE]: Latitude of the stop (WGS84). Cleaned to be numeric.
- `stop_lon` (float) [SOURCE]: Longitude of the stop (WGS84). Cleaned to be numeric.
- `valid_coords` (boolean) [DERIVED]: True if latitude is between -90 and 90, and longitude between -180 and 180. Created during cleaning.

### `bus_routes_clean.csv`
- `route_id` (string) [SOURCE, PRIMARY KEY]: Unique identifier for the route.
- `route_long_name` (string) [SOURCE]: Full name of the route.
- `agency_id` (string) [SOURCE, FOREIGN KEY]: ID of the agency operating the route.
- `route_type` (string/integer) [SOURCE]: Type of transportation used on a route (e.g., 3 for Bus).

### `bus_trips_clean.csv`
- `trip_id` (string) [SOURCE, PRIMARY KEY]: Unique identifier for a trip.
- `route_id` (string) [SOURCE, FOREIGN KEY]: ID of the route this trip belongs to.
- `service_id` (string) [SOURCE]: Identifies a set of dates when service is available for one or more routes.
- `direction_id` (string) [SOURCE]: Indicates the direction of travel for a trip.
- `trip_short_name` (string) [SOURCE]: Public facing text used to identify the trip to riders.

### `bus_stop_times_clean.csv`
- `trip_id` (string) [SOURCE, FOREIGN KEY]: Identifies a trip.
- `stop_sequence` (float/int) [SOURCE]: Order of the stops for a particular trip.
- `stop_id` (string) [SOURCE, FOREIGN KEY]: Identifies a stop.
- `arrival_time` (string) [SOURCE]: Arrival time at a specific stop (HH:MM:SS format, can exceed 24h).
- `departure_time` (string) [SOURCE]: Departure time from a specific stop (HH:MM:SS format).
- `timepoint` (string) [SOURCE]: Indicates if the time is exact or approximate.

---

## 2. Geospatial Mappings

### `bus_stops.geojson`
- Point Geometry derived directly from `stop_lon`, `stop_lat` in `bus_stops_clean.csv`.
- Properties contain `stop_id` and `stop_name`.

### `bus_routes.geojson`
- LineString Geometry derived sequentially from the stop points associated with the most representative trip of each route.
- `derived_from_stops` (boolean) [DERIVED]: Flag set to True indicating shapes.txt was unavailable.

### `bus_stops_lgd_mapping.csv`
- `stop_id` [SOURCE]
- `stop_name` [SOURCE]
- `latitude` / `longitude` [SOURCE]
- `state_code`, `state_name`... [DERIVED] Currently empty/null due to absence of geography boundary polygons.

---

## 3. Smart Cities Bus Fleet
### `smartcities_bus_fleet_clean.csv`
- `City Name` (string) [SOURCE]: Name of the smart city.
- `Type Of Bus (Ac / Non Ac)` (string) [SOURCE]: Type of bus fleet (AC or Non AC).
- `No. of buses of that type` (float) [SOURCE]: Count of buses. Commas removed, cast to float.
- `No. of bus terminals` (float) [SOURCE]: Count of bus terminals in the city. Commas removed.
- `No. of bus stands` (float) [SOURCE]: Count of bus stands. Commas removed.
- `No. of bus stops` (float) [SOURCE]: Count of bus stops. Commas removed.
