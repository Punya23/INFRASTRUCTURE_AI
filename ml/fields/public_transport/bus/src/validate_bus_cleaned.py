import os
from pathlib import Path

PROCESSED_DIR = Path(__file__).resolve().parent.parent / "data" / "processed"

required_files = [
    "agency_clean.csv",
    "stops_clean.csv",
    "routes_clean.csv",
    "trips_clean.csv",
    "stop_times_clean.csv",
    "tgsrtc_stops_clean.csv",
    "smartcities_bus_fleet_clean.csv"
]

print("=== CLEANED BUS DATA VALIDATION ===")
all_passed = True
for f in required_files:
    file_path = PROCESSED_DIR / f
    if file_path.exists() and file_path.stat().st_size > 0:
        print(f"[PASS] {f} exists and is not empty.")
    else:
        print(f"[FAIL] {f} is missing or empty.")
        all_passed = False

if all_passed:
    print("\nSUCCESS: All required cleaned files are present and valid.")
else:
    print("\nFAILURE: Some files are missing.")
    exit(1)
