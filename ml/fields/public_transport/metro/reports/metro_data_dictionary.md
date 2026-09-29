# Metro Data Dictionary

## 1. Hyderabad Metro (HMRL GTFS)

### `agency.txt`
- **agency_id** (string): Unique identifier for the agency. [SOURCE]
- **agency_name** (string): Full name of the transit agency. [SOURCE]
- **agency_url** (string): Website of the agency. [SOURCE]
- **agency_timezone** (string): Timezone in which the agency operates. [SOURCE]

### `stops.txt`
- **stop_id** (string): Unique identifier for the station. [SOURCE]
- **stop_name** (string): Name of the station. [SOURCE]
- **stop_lat** (float): Latitude of the station (WGS84). [SOURCE]
- **stop_lon** (float): Longitude of the station (WGS84). [SOURCE]

### `routes.txt`
- **route_id** (string): Unique identifier for the route. [SOURCE]
- **route_short_name** (string): Short name (e.g. Red Line). [SOURCE]
- **route_type** (integer): Type of transportation (1 = Subway/Metro). [SOURCE]

### `trips.txt`
- **trip_id** (string): Unique identifier for a trip. [SOURCE]
- **route_id** (string): Foreign key referencing `routes.txt`. [SOURCE]
- **service_id** (string): Foreign key referencing `calendar.txt`. [SOURCE]
- **shape_id** (string): Foreign key referencing `shapes.txt`. [SOURCE]

### `stop_times.txt`
- **trip_id** (string): Foreign key referencing `trips.txt`. [SOURCE]
- **stop_sequence** (integer): Order of stops on the trip. [SOURCE]
- **stop_id** (string): Foreign key referencing `stops.txt`. [SOURCE]
- **arrival_time** (string): Scheduled arrival time. [SOURCE]
- **departure_time** (string): Scheduled departure time. [SOURCE]

### `shapes.txt`
- **shape_id** (string): Unique identifier for the shape. [SOURCE]
- **shape_pt_lat** (float): Latitude of the shape point. [SOURCE]
- **shape_pt_lon** (float): Longitude of the shape point. [SOURCE]
- **shape_pt_sequence** (integer): Order of points. [SOURCE]

---

## 2. Bengaluru Metro (BMRCL)

### `bengaluru_metro_stations.kml`
- **name** (string): Name of the station extracted from Placemark. [SOURCE]
- **coordinates** (string): Longitude,Latitude,Altitude extracted from KML. [SOURCE]

### `bmrcl_station_ridership.csv`
- **code** (string): Station code. [SOURCE]
- **name** (string): Station name. [SOURCE]
*(Note: Labelled as 'ridership' but contains only station code reference data)*

---

## 3. Chennai Metro (CMRL)

### `cmrl_metro_ridership_2023_26.csv`
- **Month** (string): The month and year of the observation (e.g., Apr-23). [SOURCE]
- **Closed Loop (Ridership)** (string): Ridership using closed-loop cards (comma separated numbers). [SOURCE]
- **QR Tickets (Ridership)** (string): Ridership using QR tickets. [SOURCE]
- **Total Passenger Flow** (string): Total ridership for the month. [SOURCE]
