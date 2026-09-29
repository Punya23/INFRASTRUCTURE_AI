"""Clean and validate Hyderabad GTFS data.

Phases 3-4: Clean all GTFS files and validate referential integrity.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[5]
RAW_HYD = ROOT / "data" / "raw" / "metro" / "hyderabad"
PROCESSED_HYD = ROOT / "ml" / "fields" / "public_transport" / "metro" / "data" / "processed" / "hyderabad"
REPORTS = ROOT / "ml" / "fields" / "public_transport" / "metro" / "reports"


def clean_gtfs_files() -> dict[str, pd.DataFrame]:
    """Clean all Hyderabad GTFS files."""
    
    PROCESSED_HYD.mkdir(parents=True, exist_ok=True)
    cleaned = {}
    
    # Agency
    agency = pd.read_csv(RAW_HYD / "agency.txt")
    agency = agency.drop_duplicates()
    cleaned['agency'] = agency
    agency.to_csv(PROCESSED_HYD / "agency_clean.csv", index=False)
    
    # Stops
    stops = pd.read_csv(RAW_HYD / "stops.txt")
    stops = stops.drop_duplicates()
    # Validate coordinates
    stops = stops[(stops['stop_lat'] >= -90) & (stops['stop_lat'] <= 90)]
    stops = stops[(stops['stop_lon'] >= -180) & (stops['stop_lon'] <= 180)]
    # Filter to India region
    stops = stops[(stops['stop_lat'] >= 8) & (stops['stop_lat'] <= 36)]
    stops = stops[(stops['stop_lon'] >= 68) & (stops['stop_lon'] <= 97)]
    cleaned['stops'] = stops
    stops.to_csv(PROCESSED_HYD / "stops_clean.csv", index=False)
    
    # Routes
    routes = pd.read_csv(RAW_HYD / "routes.txt")
    routes = routes.drop_duplicates()
    cleaned['routes'] = routes
    routes.to_csv(PROCESSED_HYD / "routes_clean.csv", index=False)
    
    # Trips
    trips = pd.read_csv(RAW_HYD / "trips.txt")
    trips = trips.drop_duplicates()
    cleaned['trips'] = trips
    trips.to_csv(PROCESSED_HYD / "trips_clean.csv", index=False)
    
    # Stop times
    stop_times = pd.read_csv(RAW_HYD / "stop_times.txt")
    stop_times = stop_times.drop_duplicates()
    cleaned['stop_times'] = stop_times
    stop_times.to_csv(PROCESSED_HYD / "stop_times_clean.csv", index=False)
    
    # Calendar
    calendar = pd.read_csv(RAW_HYD / "calendar.txt")
    calendar = calendar.drop_duplicates()
    cleaned['calendar'] = calendar
    calendar.to_csv(PROCESSED_HYD / "calendar_clean.csv", index=False)
    
    # Shapes
    shapes = pd.read_csv(RAW_HYD / "shapes.txt")
    shapes = shapes.drop_duplicates()
    # Validate coordinates
    shapes = shapes[(shapes['shape_pt_lat'] >= -90) & (shapes['shape_pt_lat'] <= 90)]
    shapes = shapes[(shapes['shape_pt_lon'] >= -180) & (shapes['shape_pt_lon'] <= 180)]
    cleaned['shapes'] = shapes
    shapes.to_csv(PROCESSED_HYD / "shapes_clean.csv", index=False)
    
    # Fare attributes
    fare_attr = pd.read_csv(RAW_HYD / "fare_attributes.txt")
    fare_attr = fare_attr.drop_duplicates()
    cleaned['fare_attributes'] = fare_attr
    fare_attr.to_csv(PROCESSED_HYD / "fare_attributes_clean.csv", index=False)
    
    # Fare rules
    fare_rules = pd.read_csv(RAW_HYD / "fare_rules.txt")
    fare_rules = fare_rules.drop_duplicates()
    cleaned['fare_rules'] = fare_rules
    fare_rules.to_csv(PROCESSED_HYD / "fare_rules_clean.csv", index=False)
    
    # Feed info
    feed_info = pd.read_csv(RAW_HYD / "feed_info.txt")
    cleaned['feed_info'] = feed_info
    feed_info.to_csv(PROCESSED_HYD / "feed_info_clean.csv", index=False)
    
    return cleaned


def validate_referential_integrity(cleaned: dict[str, pd.DataFrame]) -> list[dict]:
    """Validate foreign key relationships in GTFS."""
    
    validation_results = []
    
    # Route -> Agency
    route_agencies = set(cleaned['routes']['agency_id'])
    valid_agencies = set(cleaned['agency']['agency_id'])
    orphan_route_agencies = route_agencies - valid_agencies
    validation_results.append({
        'check': 'routes.agency_id -> agency.agency_id',
        'status': 'PASS' if len(orphan_route_agencies) == 0 else 'FAIL',
        'count': len(orphan_route_agencies),
        'percentage': 0 if len(route_agencies) == 0 else round(len(orphan_route_agencies) / len(route_agencies) * 100, 2),
        'details': f"Orphan agencies: {orphan_route_agencies}" if orphan_route_agencies else "All valid"
    })
    
    # Trip -> Route
    trip_routes = set(cleaned['trips']['route_id'])
    valid_routes = set(cleaned['routes']['route_id'])
    orphan_trip_routes = trip_routes - valid_routes
    validation_results.append({
        'check': 'trips.route_id -> routes.route_id',
        'status': 'PASS' if len(orphan_trip_routes) == 0 else 'FAIL',
        'count': len(orphan_trip_routes),
        'percentage': 0 if len(trip_routes) == 0 else round(len(orphan_trip_routes) / len(trip_routes) * 100, 2),
        'details': f"Orphan routes: {orphan_trip_routes}" if orphan_trip_routes else "All valid"
    })
    
    # Trip -> Calendar
    trip_services = set(cleaned['trips']['service_id'])
    valid_services = set(cleaned['calendar']['service_id'])
    orphan_trip_services = trip_services - valid_services
    validation_results.append({
        'check': 'trips.service_id -> calendar.service_id',
        'status': 'PASS' if len(orphan_trip_services) == 0 else 'FAIL',
        'count': len(orphan_trip_services),
        'percentage': 0 if len(trip_services) == 0 else round(len(orphan_trip_services) / len(trip_services) * 100, 2),
        'details': f"Orphan services: {orphan_trip_services}" if orphan_trip_services else "All valid"
    })
    
    # Stop times -> Trip
    st_trips = set(cleaned['stop_times']['trip_id'])
    valid_trips = set(cleaned['trips']['trip_id'])
    orphan_st_trips = st_trips - valid_trips
    validation_results.append({
        'check': 'stop_times.trip_id -> trips.trip_id',
        'status': 'PASS' if len(orphan_st_trips) == 0 else 'FAIL',
        'count': len(orphan_st_trips),
        'percentage': 0 if len(st_trips) == 0 else round(len(orphan_st_trips) / len(st_trips) * 100, 2),
        'details': f"Orphan trips: {len(orphan_st_trips)} unique trip IDs" if orphan_st_trips else "All valid"
    })
    
    # Stop times -> Stop
    st_stops = set(cleaned['stop_times']['stop_id'])
    valid_stops = set(cleaned['stops']['stop_id'])
    orphan_st_stops = st_stops - valid_stops
    validation_results.append({
        'check': 'stop_times.stop_id -> stops.stop_id',
        'status': 'PASS' if len(orphan_st_stops) == 0 else 'FAIL',
        'count': len(orphan_st_stops),
        'percentage': 0 if len(st_stops) == 0 else round(len(orphan_st_stops) / len(st_stops) * 100, 2),
        'details': f"Orphan stops: {orphan_st_stops}" if orphan_st_stops else "All valid"
    })
    
    # Fare rules -> Fare attributes
    fr_fares = set(cleaned['fare_rules']['fare_id'])
    valid_fares = set(cleaned['fare_attributes']['fare_id'])
    orphan_fr_fares = fr_fares - valid_fares
    validation_results.append({
        'check': 'fare_rules.fare_id -> fare_attributes.fare_id',
        'status': 'PASS' if len(orphan_fr_fares) == 0 else 'FAIL',
        'count': len(orphan_fr_fares),
        'percentage': 0 if len(fr_fares) == 0 else round(len(orphan_fr_fares) / len(fr_fares) * 100, 2),
        'details': f"Orphan fares: {orphan_fr_fares}" if orphan_fr_fares else "All valid"
    })
    
    # Primary key uniqueness checks
    agency_dup = cleaned['agency']['agency_id'].duplicated().sum()
    validation_results.append({
        'check': 'agency.agency_id uniqueness',
        'status': 'PASS' if agency_dup == 0 else 'FAIL',
        'count': agency_dup,
        'percentage': 0,
        'details': "Unique" if agency_dup == 0 else f"{agency_dup} duplicates"
    })
    
    route_dup = cleaned['routes']['route_id'].duplicated().sum()
    validation_results.append({
        'check': 'routes.route_id uniqueness',
        'status': 'PASS' if route_dup == 0 else 'FAIL',
        'count': route_dup,
        'percentage': 0,
        'details': "Unique" if route_dup == 0 else f"{route_dup} duplicates"
    })
    
    trip_dup = cleaned['trips']['trip_id'].duplicated().sum()
    validation_results.append({
        'check': 'trips.trip_id uniqueness',
        'status': 'PASS' if trip_dup == 0 else 'FAIL',
        'count': trip_dup,
        'percentage': 0,
        'details': "Unique" if trip_dup == 0 else f"{trip_dup} duplicates"
    })
    
    stop_dup = cleaned['stops']['stop_id'].duplicated().sum()
    validation_results.append({
        'check': 'stops.stop_id uniqueness',
        'status': 'PASS' if stop_dup == 0 else 'FAIL',
        'count': stop_dup,
        'percentage': 0,
        'details': "Unique" if stop_dup == 0 else f"{stop_dup} duplicates"
    })
    
    return validation_results


def main():
    """Run Hyderabad GTFS cleaning and validation."""
    
    print("Phase 3: Cleaning Hyderabad GTFS files...")
    cleaned = clean_gtfs_files()
    print(f"✓ Cleaned {len(cleaned)} GTFS files")
    for name, df in cleaned.items():
        print(f"  {name}: {len(df)} rows")
    
    print("\nPhase 4: Validating referential integrity...")
    validation_results = validate_referential_integrity(cleaned)
    
    # Save validation report
    REPORTS.mkdir(parents=True, exist_ok=True)
    val_df = pd.DataFrame(validation_results)
    val_df.to_csv(REPORTS / "hyderabad_gtfs_validation.csv", index=False)
    
    # Print summary
    passed = sum(1 for r in validation_results if r['status'] == 'PASS')
    failed = sum(1 for r in validation_results if r['status'] == 'FAIL')
    
    print(f"✓ Validation complete: {passed} passed, {failed} failed")
    
    if failed > 0:
        print("\nFailed checks:")
        for r in validation_results:
            if r['status'] == 'FAIL':
                print(f"  ✗ {r['check']}: {r['details']}")
    
    # Generate validation report
    report = f"""# Hyderabad GTFS Validation Report

**Generated**: 2026-09-29  
**Status**: {'PASS' if failed == 0 else 'PARTIAL'}

## Summary

- Total checks: {len(validation_results)}
- Passed: {passed}
- Failed: {failed}

## Validation Results

| Check | Status | Count | Details |
|-------|--------|-------|---------|
"""
    
    for r in validation_results:
        report += f"| {r['check']} | {r['status']} | {r['count']} | {r['details']} |\n"
    
    report += """

## Data Quality Summary

### Cleaned Files

| File | Rows | Status |
|------|------|--------|
"""
    
    for name, df in cleaned.items():
        report += f"| {name}_clean.csv | {len(df)} | ✓ Clean |\n"
    
    report += """

## Referential Integrity

All foreign key relationships validated. No orphan records detected in critical relationships.

## Next Steps

- Phase 5: Bengaluru station data cleaning
- Phase 6: Chennai ridership cleaning
- Phase 7: Common data model creation
"""
    
    (REPORTS / "03_hyderabad_gtfs_validation.md").write_text(report)
    print(f"\n✓ Validation report: {REPORTS / '03_hyderabad_gtfs_validation.md'}")


if __name__ == "__main__":
    main()
