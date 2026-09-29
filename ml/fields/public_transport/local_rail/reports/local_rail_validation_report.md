# Local Rail Raw Data Validation Report

**Date**: 2026-09-29  
**Status**: PARTIAL

## Mumbai Suburban Railway

### Files Validated

**mumbai_suburban_lines.kml**:
- Valid XML: ✓
- Valid KML: ✓
- Placemarks: 106
- Geometry Type: LineString
- Has Coordinates: ✓

**mumbai_suburban_stations.kml**:
- Valid XML: ✓
- Valid KML: ✓
- Placemarks: 106
- Geometry Type: Point
- Has Coordinates: ✓

## Chennai Suburban Railway

**Status**: DATA_UNAVAILABLE

The collected GTFS file contains MTC (buses) and CMRL (metro) data.  
It **DOES NOT** contain Chennai suburban railway (Southern Railway EMU) data.

Therefore: **Chennai suburban rail cannot be analyzed** with current data.

## Kolkata Suburban Railway

**Status**: DATA_UNAVAILABLE - No machine-readable data found.

## Hyderabad MMTS

**Status**: DATA_UNAVAILABLE - No machine-readable data found.

## Pune Suburban Railway

**Status**: DATA_UNAVAILABLE - No machine-readable data found.

---

## Validation Summary

| System | Data Status | Validation Status |
|--------|-------------|-------------------|
| Mumbai | ✓ Available | ✓ PASS |
| Chennai | ✗ Unavailable | N/A |
| Kolkata | ✗ Unavailable | N/A |
| Hyderabad MMTS | ✗ Unavailable | N/A |
| Pune | ✗ Unavailable | N/A |
