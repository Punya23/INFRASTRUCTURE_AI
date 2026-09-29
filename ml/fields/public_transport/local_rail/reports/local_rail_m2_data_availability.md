# LOCAL RAIL — M2 Data Availability Report

**Domain:** Local Rail (Suburban Railway Systems)  
**Report Date:** 2026-09-29  
**Milestone:** M2 — Deep EDA + Infrastructure Features  
**Geographic Scope:** 5 suburban railway systems across India

---

## Executive Summary

This report documents the comprehensive data availability status for all 5 suburban railway systems after M2 analysis. Only **Mumbai Suburban Railway** has machine-readable infrastructure data (stations + line geometry). The other four systems remain **DATA_UNAVAILABLE**.

**Overall Status:** 1 of 5 systems (20%) with PARTIAL data availability.

---

## Data Availability Matrix

| System | State | City | Stations | Coordinates | Line Geometry | Route Data | Service Data | Timetable | Frequency | Ridership | Population | LGD | Accessibility | **Status** |
|--------|-------|------|----------|-------------|---------------|------------|--------------|-----------|-----------|-----------|------------|-----|---------------|------------|
| **Mumbai Suburban** | Maharashtra | Mumbai | ✓ | ✓ (PARTIAL) | ✓ | UNKNOWN | ✗ | ✗ | ✗ | ✗ | NOT_YET | NOT_YET | NOT_YET | **PARTIAL** |
| **Chennai Suburban** | Tamil Nadu | Chennai | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | NOT_YET | NOT_YET | NOT_YET | **UNAVAILABLE** |
| **Kolkata Suburban** | West Bengal | Kolkata | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | NOT_YET | NOT_YET | NOT_YET | **UNAVAILABLE** |
| **Hyderabad MMTS** | Telangana | Hyderabad | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | NOT_YET | NOT_YET | NOT_YET | **UNAVAILABLE** |
| **Pune Suburban** | Maharashtra | Pune | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | NOT_YET | NOT_YET | NOT_YET | **UNAVAILABLE** |

**Legend:**
- ✓ = Data available and validated
- PARTIAL = Data available but incomplete (see notes)
- UNKNOWN = Partially available but unusable (e.g., line names without station mappings)
- ✗ = Not available (no official source found)
- NOT_YET = Analysis not yet performed (requires M3 or separate data collection)

---

## Mumbai Suburban Railway — Detailed Breakdown

### ✓ Available (6 attributes)
1. **Stations:** 106 stations with IDs, names
2. **Coordinates:** 106 station coordinates (lat/lon)
3. **Line Geometry:** 106 line segments (307 km total)
4. **Provenance:** 100% source metadata (source, source_file, source_url)
5. **Geospatial Analysis:** GeoJSON files, bounding box, spacing
6. **Infrastructure Features:** Station-level features (validity, spacing, provenance)

### ⚠ Partially Available (1 attribute)
7. **Coordinates (Quality):** 100% valid after M2 re-investigation (M1 incorrectly flagged 34 stations as "out of range")

### ⚠ Available but Unusable (1 attribute)
8. **Route Data:** Line names present (Western/Central/Harbour/Trans-Harbour) but no station-to-line mapping

### ✗ Unavailable (5 attributes)
9. **Service Data:** No train service metadata (route schedules, service IDs)
10. **Timetables:** No first/last train timings per station
11. **Frequency:** No peak/off-peak trains-per-hour data
12. **Ridership:** No daily/annual passenger counts per station
13. **Interchange Flags:** No data on which stations connect multiple lines

### 🕐 Not Yet Joined (3 attributes)
14. **Population:** Requires LGD city boundaries + Census data (M3 task)
15. **LGD Codes:** Requires geography layer join (M3 task)
16. **Accessibility:** Requires population + boundary analysis (M3 task)

---

## Mumbai — M2 Findings Summary

### Infrastructure Data Quality
| Metric | Value | Assessment |
|--------|-------|------------|
| **Stations** | 106 | Complete |
| **Coordinate validity** | 100% | Excellent (revised from M1's 67.9%) |
| **Line segments** | 106 | Complete |
| **Network length** | 307.46 km | Validated |
| **Geometry validity** | 100% | Excellent |
| **Provenance completeness** | 100% | Excellent |

### Service Data Gaps
| Attribute | Status | Impact |
|-----------|--------|--------|
| **Ridership** | UNAVAILABLE | Cannot calculate demand, peak usage, or crowding |
| **Frequency** | UNAVAILABLE | Cannot assess service quality or capacity |
| **Timetables** | UNAVAILABLE | Cannot determine operating hours or first/last trains |
| **Route mapping** | PARTIAL | Cannot assign stations to specific lines (Western vs Central) |
| **Interchange flags** | UNAVAILABLE | Cannot identify transfer stations for multimodal analysis |

---

## Chennai Suburban Railway — Status

### System Overview
- **Operator:** Southern Railway (Indian Railways zone)
- **Estimated Extent:** ~48 stations across 4 corridors (Arakkonam–Chennai Beach–Tambaram lines)
- **Status:** **DATA_UNAVAILABLE**

### Data Search Results (from M1)
| Source | Format | Status | Notes |
|--------|--------|--------|-------|
| UngalSoththu GTFS | GTFS | ✗ Excludes suburban rail | Contains MTC buses + CMRL metro only |
| Indian Railways website | HTML/PDF | ✗ Non-geographic | Only textual timetables |
| NTES API | JSON | ⚠ Not investigated | Potential future source |
| OpenStreetMap | Overpass API | ⚠ Not investigated | May have partial rail geometry |

### Recommendations
1. **Immediate:** Contact Southern Railway Chennai division for official station list + route maps
2. **Alternative:** Parse NTES (National Train Enquiry System) API for suburban train data
3. **Fallback:** Extract rail geometry from OpenStreetMap + manually geocode stations from timetables

---

## Kolkata Suburban Railway — Status

### System Overview
- **Operator:** Eastern Railway + South Eastern Railway (Indian Railways zones)
- **Estimated Extent:** ~120 stations across Sealdah South/North + Howrah lines
- **Status:** **DATA_UNAVAILABLE**

### Data Search Results (from M1)
| Source | Format | Status | Notes |
|--------|--------|--------|-------|
| Indian Railways website | HTML/PDF | ✗ Non-geographic | Only textual timetables |
| OpenStreetMap | Overpass API | ⚠ Partial | Rail lines present, station metadata incomplete |
| GTFS feeds | GTFS | ✗ Not found | No public GTFS for Kolkata suburban rail |

### Recommendations
1. **Immediate:** Contact Eastern Railway / South Eastern Railway for official data
2. **Alternative:** Extract geometry from OpenStreetMap + cross-reference with timetable PDFs
3. **Fallback:** Manually geocode ~120 stations from official railway maps

---

## Hyderabad MMTS — Status

### System Overview
- **Operator:** South Central Railway + HMRL
- **Estimated Extent:** ~20 stations, 3 lines, ~45 km
- **Status:** **DATA_UNAVAILABLE**

### Data Search Results (from M1)
| Source | Format | Status | Notes |
|--------|--------|--------|-------|
| HMRL website | HTML | ✗ Non-geographic | Only route descriptions |
| Indian Railways website | PDF | ✗ Non-geographic | Timetables without coordinates |
| GTFS feeds | GTFS | ✗ Not found | No public GTFS for MMTS |

### Recommendations
1. **Immediate:** Contact HMRL or South Central Railway for station data
2. **Alternative:** Cross-reference MMTS routes with Hyderabad Metro GTFS for interchanges
3. **Fallback:** Manually geocode ~20 stations (small network, feasible)

---

## Pune Suburban Railway — Status

### System Overview
- **Operator:** Central Railway (Indian Railways zone)
- **Estimated Extent:** ~10-15 stations, primarily Pune–Lonavla corridor
- **Status:** **DATA_UNAVAILABLE**

### Data Search Results (from M1)
| Source | Format | Status | Notes |
|--------|--------|--------|-------|
| Indian Railways website | HTML/PDF | ✗ Non-geographic | Only textual timetables |
| GTFS feeds | GTFS | ✗ Not found | No public GTFS for Pune suburban rail |

### Recommendations
1. **Immediate:** Contact Central Railway Pune division for station data
2. **Alternative:** Extract data from NTES API for Pune local trains
3. **Fallback:** Manually geocode ~10-15 stations (very small network)

---

## Cross-System Comparison

| System | Estimated Stations | Estimated Length | Data Availability | Priority |
|--------|-------------------|------------------|-------------------|----------|
| **Mumbai** | 106 (verified) | 307 km (verified) | **PARTIAL** | ✓ Ready for M3 |
| **Chennai** | ~48 (est.) | ~200 km (est.) | **UNAVAILABLE** | High |
| **Kolkata** | ~120 (est.) | ~300 km (est.) | **UNAVAILABLE** | High |
| **Hyderabad MMTS** | ~20 (est.) | ~45 km (est.) | **UNAVAILABLE** | Medium |
| **Pune** | ~15 (est.) | ~50 km (est.) | **UNAVAILABLE** | Low |

**Total Estimated:** ~309 stations, ~902 km suburban rail infrastructure across 5 systems  
**Current Coverage:** 106 stations (34%), 307 km (34%) — Mumbai only

---

## Missing Data Impact Assessment

### Blocked Analyses (Mumbai)
- **Ridership Analysis:** Cannot calculate peak demand, crowding indices, or station rankings
- **Service Quality:** Cannot assess frequency, reliability, or coverage
- **Multimodal Integration:** Cannot identify metro+suburban rail interchange stations
- **Temporal Analysis:** Cannot determine service hours, peak vs off-peak patterns
- **Capacity Planning:** Cannot estimate spare capacity or congestion hotspots

### Blocked Systems (Chennai/Kolkata/Hyderabad/Pune)
- **All analyses blocked** — no infrastructure data (stations, geometry) available
- **Population accessibility:** Cannot calculate suburban rail coverage for these cities
- **Gap identification:** Cannot determine underserved areas or expansion priorities

---

## Data Collection Recommendations

### Mumbai (Enhance Existing Data)
1. **Western Railway / Central Railway annual reports:** Source ridership data
2. **Indian Railways GTFS:** Check if Mumbai Suburban GTFS exists (unreported)
3. **NTES API integration:** Extract timetable + service frequency data
4. **Manual annotation:** Map stations to lines using official railway maps

### Other Systems (New Data Collection)
1. **Official Railway Engagement:**
   - Chennai: Contact Southern Railway Chennai division
   - Kolkata: Contact Eastern Railway / South Eastern Railway
   - Hyderabad: Contact HMRL or South Central Railway
   - Pune: Contact Central Railway Pune division

2. **NTES API Scraping:** Build automated extractor for suburban train data (all cities)

3. **OpenStreetMap Extraction:** Extract rail geometry + station locations where available (Kolkata partial)

4. **Manual Geocoding:** Last resort for small networks (Hyderabad ~20 stations, Pune ~15 stations)

---

## M3 Readiness Assessment

### Mumbai Suburban Railway
**M3 Ready:** ✓ YES (with limitations)

**Ready Components:**
- ✓ Station locations (106 coordinates, 100% valid)
- ✓ Network geometry (307 km line segments)
- ✓ Infrastructure features (spacing, density, coverage)

**M3 Requirements:**
- **LGD City Boundaries:** NOT_YET_AVAILABLE (required for population catchment)
- **Census Population Data:** NOT_YET_JOINED (required for demand estimation)
- **Service Area Polygons:** CAN_BE_GENERATED (buffer analysis around stations)

**M3 Blocked Analyses:**
- Population per station: Blocked by missing LGD boundaries
- Stations per 100k population: Blocked by missing population data
- Underserved population: Blocked by missing boundaries + population

**M3 Achievable Analyses:**
- Geographic coverage area (buffer analysis)
- Station density by district (if district boundaries available)
- Accessibility isochrones (theoretical, without actual service frequency)

### Other Systems
**M3 Ready:** ✗ NO

**Reason:** No infrastructure data (stations, geometry) available. M3 cannot proceed without M1 completion.

---

## Conclusion

Mumbai Suburban Railway is the **only system** with PARTIAL data availability (infrastructure topology complete, service data unavailable). The other four systems remain **completely blocked by DATA_UNAVAILABLE** — no stations, no geometry, no service data.

**Critical Finding:** Indian Railways suburban operations **lack centralized open data infrastructure** comparable to:
- Metro systems (12/15 metro systems have GTFS feeds)
- National Highways (NHAI GeoServer provides comprehensive road data)

**Recommendation:** Proceed to **M3 with Mumbai only**. Other systems require direct Indian Railways engagement or manual data collection before M3 can begin.

---

**Report Author:** Kiro AI Agent  
**Report Date:** 2026-09-29  
**Next Steps:** Create M2 audit report, commit M2 work to git, assess M3 readiness
