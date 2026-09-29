import json
from pathlib import Path

import pandas as pd

PROCESSED_DIR = Path("ml/fields/public_transport/bus/data/processed")
REPORTS_DIR = Path("ml/fields/public_transport/bus/reports")

required_files = [
    "bus_agency_clean.csv",
    "bus_stops_clean.csv",
    "bus_routes_clean.csv",
    "bus_trips_clean.csv",
    "bus_stop_times_clean.csv",
    "bus_tgsrtc_stops_clean.csv",
    "smartcities_bus_fleet_clean.csv",
    "bus_stops.geojson",
    "bus_routes.geojson",
    "bus_stops_lgd_mapping.csv",
    "bus_route_lgd_mapping.csv"
]

print("=== CLEANED BUS DATA VALIDATION ===")
all_passed = True
report = {}

for f in required_files:
    file_path = PROCESSED_DIR / f
    if file_path.exists() and file_path.stat().st_size > 0:
        report[f] = "PASS"
        print(f"[PASS] {f} exists and is not empty.")
    else:
        report[f] = "FAIL"
        print(f"[FAIL] {f} is missing or empty.")
        all_passed = False

if all_passed:
    print("\nSUCCESS: All required cleaned files are present and valid.")
else:
    print("\nFAILURE: Some files are missing.")

# GTFS referential checks
print("\nRunning GTFS integrity checks...")
try:
    stops = pd.read_csv(PROCESSED_DIR / 'bus_stops_clean.csv')
    routes = pd.read_csv(PROCESSED_DIR / 'bus_routes_clean.csv')
    trips = pd.read_csv(PROCESSED_DIR / 'bus_trips_clean.csv')
    st = pd.read_csv(PROCESSED_DIR / 'bus_stop_times_clean.csv')
    
    orphan_routes = set(trips['route_id']) - set(routes['route_id'])
    orphan_trips = set(st['trip_id']) - set(trips['trip_id'])
    orphan_stops = set(st['stop_id']) - set(stops['stop_id'])
    
    if orphan_routes:
        report['GTFS_Integrity_Routes'] = f"FAIL (Orphaned routes: {len(orphan_routes)})"
    else:
        report['GTFS_Integrity_Routes'] = "PASS"
        
    if orphan_trips:
        report['GTFS_Integrity_Trips'] = f"FAIL (Orphaned trips: {len(orphan_trips)})"
    else:
        report['GTFS_Integrity_Trips'] = "PASS"
        
    if orphan_stops:
        report['GTFS_Integrity_Stops'] = f"FAIL (Orphaned stops: {len(orphan_stops)})"
    else:
        report['GTFS_Integrity_Stops'] = "PASS"
        
    print(f"Routes Integrity: {report['GTFS_Integrity_Routes']}")
    print(f"Trips Integrity: {report['GTFS_Integrity_Trips']}")
    print(f"Stops Integrity: {report['GTFS_Integrity_Stops']}")

except (OSError, KeyError, ValueError) as e:  # missing file/column or unparsable CSV
    report['GTFS_Integrity'] = f"FAIL ({e!s})"
    print("FAILED GTFS Integrity Checks.")

with open(REPORTS_DIR / "bus_validation_report.json", "w") as f:
    json.dump(report, f, indent=4)
    
with open(REPORTS_DIR / "bus_validation_report.md", "w") as f:
    f.write("# Bus Validation Report\n\n")
    f.writelines(f"- **{k}**: {v}\n" for k, v in report.items())
