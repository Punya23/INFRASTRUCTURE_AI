import zipfile
from pathlib import Path

import pandas as pd

# Paths
ROOT_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT_DIR.parent.parent.parent.parent / "data" / "raw"
BUS_RAW = RAW_DIR / "bus"
PROCESSED_DIR = ROOT_DIR / "data" / "processed"
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR = ROOT_DIR / "reports"

GTFS_PATH = BUS_RAW / "tgsrtc" / "telangana_opendata_gtfs_tgsrtc_08_february_2026.zip"
TGSRTC_STOPS_CSV = BUS_RAW / "tgsrtc" / "hyd_stops.csv"
FLEET_CSV = BUS_RAW / "ogd" / "smartcities_bus_fleet.csv"

def clean_gtfs():
    print("Cleaning GTFS...")
    with zipfile.ZipFile(GTFS_PATH, 'r') as z:
        # agency
        if "agency.txt" in z.namelist():
            agency = pd.read_csv(z.open("agency.txt"))
            agency.columns = [c.strip() for c in agency.columns]
            for col in agency.select_dtypes(['object']).columns:
                agency[col] = agency[col].astype(str).str.strip()
            agency.to_csv(PROCESSED_DIR / "agency_clean.csv", index=False)
            print(f"Agency: {len(agency)} rows")
        
        # stops
        if "stops.txt" in z.namelist():
            stops = pd.read_csv(z.open("stops.txt"))
            stops.columns = [c.strip() for c in stops.columns]
            for col in stops.select_dtypes(['object']).columns:
                stops[col] = stops[col].astype(str).str.strip()
            # Drop purely empty stop_id
            stops = stops.dropna(subset=['stop_id'])
            # Ensure coordinates are numeric
            stops['stop_lat'] = pd.to_numeric(stops['stop_lat'], errors='coerce')
            stops['stop_lon'] = pd.to_numeric(stops['stop_lon'], errors='coerce')
            # Identify invalid coordinates
            valid_mask = (stops['stop_lat'] >= -90) & (stops['stop_lat'] <= 90) & (stops['stop_lon'] >= -180) & (stops['stop_lon'] <= 180)
            stops['valid_coords'] = valid_mask
            stops.to_csv(PROCESSED_DIR / "stops_clean.csv", index=False)
            print(f"Stops: {len(stops)} rows, {stops['valid_coords'].sum()} valid coords")
            
        # routes
        if "routes.txt" in z.namelist():
            routes = pd.read_csv(z.open("routes.txt"))
            routes.columns = [c.strip() for c in routes.columns]
            for col in routes.select_dtypes(['object']).columns:
                routes[col] = routes[col].astype(str).str.strip()
            routes.to_csv(PROCESSED_DIR / "routes_clean.csv", index=False)
            print(f"Routes: {len(routes)} rows")
            
        # trips
        if "trips.txt" in z.namelist():
            trips = pd.read_csv(z.open("trips.txt"))
            trips.columns = [c.strip() for c in trips.columns]
            for col in trips.select_dtypes(['object']).columns:
                trips[col] = trips[col].astype(str).str.strip()
            trips.to_csv(PROCESSED_DIR / "trips_clean.csv", index=False)
            print(f"Trips: {len(trips)} rows")
            
        # stop_times
        if "stop_times.txt" in z.namelist():
            stop_times = pd.read_csv(z.open("stop_times.txt"), dtype=str)
            stop_times.columns = [c.strip() for c in stop_times.columns]
            for col in stop_times.select_dtypes(['object']).columns:
                stop_times[col] = stop_times[col].astype(str).str.strip()
            stop_times['stop_sequence'] = pd.to_numeric(stop_times['stop_sequence'], errors='coerce')
            stop_times.to_csv(PROCESSED_DIR / "stop_times_clean.csv", index=False)
            print(f"Stop Times: {len(stop_times)} rows")
            
        # calendar
        if "calendar.txt" in z.namelist():
            cal = pd.read_csv(z.open("calendar.txt"))
            cal.columns = [c.strip() for c in cal.columns]
            for col in cal.select_dtypes(['object']).columns:
                cal[col] = cal[col].astype(str).str.strip()
            cal.to_csv(PROCESSED_DIR / "calendar_clean.csv", index=False)
            print(f"Calendar: {len(cal)} rows")
            
        # feed_info
        if "feed_info.txt" in z.namelist():
            feed = pd.read_csv(z.open("feed_info.txt"))
            feed.to_csv(PROCESSED_DIR / "feed_info_clean.csv", index=False)

def clean_tgsrtc_stops():
    print("Cleaning TGSRTC Stops CSV...")
    if TGSRTC_STOPS_CSV.exists():
        stops = pd.read_csv(TGSRTC_STOPS_CSV)
        stops.columns = [c.strip() for c in stops.columns]
        for col in stops.select_dtypes(['object']).columns:
            stops[col] = stops[col].astype(str).str.strip()
        
        stops['stop_lat'] = pd.to_numeric(stops['stop_lat'], errors='coerce')
        stops['stop_lon'] = pd.to_numeric(stops['stop_lon'], errors='coerce')
        valid_mask = (stops['stop_lat'] >= -90) & (stops['stop_lat'] <= 90) & (stops['stop_lon'] >= -180) & (stops['stop_lon'] <= 180)
        stops['valid_coords'] = valid_mask
        
        stops.to_csv(PROCESSED_DIR / "tgsrtc_stops_clean.csv", index=False)
        print(f"TGSRTC Stops CSV: {len(stops)} rows")

def clean_fleet():
    print("Cleaning Smart Cities Fleet CSV...")
    if FLEET_CSV.exists():
        fleet = pd.read_csv(FLEET_CSV)
        fleet.columns = [c.strip() for c in fleet.columns]
        for col in fleet.select_dtypes(['object']).columns:
            fleet[col] = fleet[col].astype(str).str.strip()
            # replace '-' with NaN
            fleet[col] = fleet[col].replace({'-': None, '': None, 'nan': None, 'NaN': None})
            
        # Convert numeric columns
        numeric_cols = ['No. of buses of that type', 'No. of bus terminals', 'No. of bus stands', 'No. of bus stops']
        for col in numeric_cols:
            if col in fleet.columns:
                # Remove commas
                if fleet[col].dtype == 'object':
                    fleet[col] = fleet[col].str.replace(',', '')
                fleet[col] = pd.to_numeric(fleet[col], errors='coerce')
                
        fleet.to_csv(PROCESSED_DIR / "smartcities_bus_fleet_clean.csv", index=False)
        print(f"Smart Cities Fleet: {len(fleet)} rows")

if __name__ == "__main__":
    clean_gtfs()
    clean_tgsrtc_stops()
    clean_fleet()
