# Step 2: Bus Data Dictionary

## 1. TGSRTC GTFS

### `agency_clean.csv`
- `agency_id` (string): Unique identifier for the agency.
- `agency_name` (string): Full name of the transit agency.
- `agency_url` (string): Website of the agency.
- `agency_timezone` (string): Timezone in which the agency operates.
- `agency_lang` (string): Primary language used by the agency.

### `stops_clean.csv`
- `stop_id` (string): Unique identifier for the stop.
- `stop_name` (string): Name of the stop.
- `stop_lat` (float): Latitude of the stop (WGS84). Cleaned to be numeric.
- `stop_lon` (float): Longitude of the stop (WGS84). Cleaned to be numeric.
- `valid_coords` (boolean): True if latitude is between -90 and 90, and longitude between -180 and 180. Created during cleaning.

### `routes_clean.csv`
- `route_id` (string): Unique identifier for the route.
- `route_long_name` (string): Full name of the route.
- `agency_id` (string): ID of the agency operating the route.
- `route_type` (string/integer): Type of transportation used on a route (e.g., 3 for Bus).

### `trips_clean.csv`
- `trip_id` (string): Unique identifier for a trip.
- `route_id` (string): ID of the route this trip belongs to.
- `service_id` (string): Identifies a set of dates when service is available for one or more routes.
- `direction_id` (string): Indicates the direction of travel for a trip.
- `trip_short_name` (string): Public facing text used to identify the trip to riders.

### `stop_times_clean.csv`
- `trip_id` (string): Identifies a trip.
- `stop_sequence` (float/int): Order of the stops for a particular trip.
- `stop_id` (string): Identifies a stop.
- `arrival_time` (string): Arrival time at a specific stop (HH:MM:SS format, can exceed 24h).
- `departure_time` (string): Departure time from a specific stop (HH:MM:SS format).
- `timepoint` (string): Indicates if the time is exact or approximate.

---

## 2. TGSRTC Stops CSV
### `tgsrtc_stops_clean.csv`
- `stop_id` (string): Identifier.
- `stop_name` (string): Stop name.
- `zone_id` (string): Zone identifier.
- `stop_lat` (float): Latitude (WGS84).
- `stop_lon` (float): Longitude (WGS84).
- `stop_desc` (string): Description of the stop.
- `valid_coords` (boolean): Added mask for valid lat/lon.

---

## 3. Smart Cities Bus Fleet
### `smartcities_bus_fleet_clean.csv`
- `City Name` (string): Name of the smart city.
- `Type Of Bus (Ac / Non Ac)` (string): Type of bus fleet (AC or Non AC).
- `No. of buses of that type` (float): Count of buses. Commas removed, cast to float.
- `No. of bus terminals` (float): Count of bus terminals in the city. Commas removed.
- `No. of bus stands` (float): Count of bus stands. Commas removed.
- `No. of bus stops` (float): Count of bus stops. Commas removed.
