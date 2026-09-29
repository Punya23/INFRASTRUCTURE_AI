# Hyderabad GTFS Validation Report

**Generated**: 2026-09-29  
**Status**: PASS

## Summary

- Total checks: 10
- Passed: 10
- Failed: 0

## Validation Results

| Check | Status | Count | Details |
|-------|--------|-------|---------|
| routes.agency_id -> agency.agency_id | PASS | 0 | All valid |
| trips.route_id -> routes.route_id | PASS | 0 | All valid |
| trips.service_id -> calendar.service_id | PASS | 0 | All valid |
| stop_times.trip_id -> trips.trip_id | PASS | 0 | All valid |
| stop_times.stop_id -> stops.stop_id | PASS | 0 | All valid |
| fare_rules.fare_id -> fare_attributes.fare_id | PASS | 0 | All valid |
| agency.agency_id uniqueness | PASS | 0 | Unique |
| routes.route_id uniqueness | PASS | 0 | Unique |
| trips.trip_id uniqueness | PASS | 0 | Unique |
| stops.stop_id uniqueness | PASS | 0 | Unique |


## Data Quality Summary

### Cleaned Files

| File | Rows | Status |
|------|------|--------|
| agency_clean.csv | 1 | ✓ Clean |
| stops_clean.csv | 705 | ✓ Clean |
| routes_clean.csv | 3 | ✓ Clean |
| trips_clean.csv | 2820 | ✓ Clean |
| stop_times_clean.csv | 61236 | ✓ Clean |
| calendar_clean.csv | 3 | ✓ Clean |
| shapes_clean.csv | 2450 | ✓ Clean |
| fare_attributes_clean.csv | 10 | ✓ Clean |
| fare_rules_clean.csv | 3249 | ✓ Clean |
| feed_info_clean.csv | 1 | ✓ Clean |


## Referential Integrity

All foreign key relationships validated. No orphan records detected in critical relationships.

## Next Steps

- Phase 5: Bengaluru station data cleaning
- Phase 6: Chennai ridership cleaning
- Phase 7: Common data model creation
