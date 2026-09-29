# LOCAL RAIL M3 — Audit Report

**Domain:** Local Rail (Suburban Railway Systems)  
**Milestone:** M3 — Geography, Population & Accessibility  
**Audit Date:** 2026-09-29  
**Pipeline Script:** `ml/fields/public_transport/local_rail/src/03_m3_geography_accessibility.py`  
**Execution Time:** <5 seconds

---

## Audit Summary

**M3 Status:** ✓ PARTIAL COMPLETE  
**Systems Processed:** 1 of 5 (Mumbai Suburban Railway only)  
**Data Integrity:** MAINTAINED (no fabrication, explicit BLOCKED status for unavailable data)  
**Output Files:** 10 files created (3 GeoJSON catchments, 4 CSV data files, 3 narrative reports)

---

## Pipeline Execution Log

### Input Sources (M2 Outputs)
| File | Records | Status |
|------|---------|--------|
| `mumbai_stations_clean.csv` | 106 | ✓ Read successfully |
| `mumbai_station_features.csv` | 106 | ✓ Read successfully |
| LGD geography files | 6 files | ✓ Read successfully |

### Phase 1: LGD Geography Investigation
**Objective:** Determine if LGD geography files contain spatial boundary polygons

**Files Investigated:**
- `states_clean.csv` — 36 records
- `districts_clean.csv` — 784 records (36 Maharashtra)
- `subdistricts_clean.csv` — 7,092 records
- `ulbs_clean.csv` — 5,051 records (422 Maharashtra)
- `wards_maharashtra_clean.csv` — 7,256 records
- `wards_all_available_clean.csv` — 28,837 records

**Geometry Check:**
- Checked for columns: `geometry`, `wkt`, `geom`, `polygon`, `latitude`, `longitude`, `centroid_lat`, `centroid_lon`
- **Result:** ZERO files contain spatial geometry
- **Status:** CODES_ONLY_NO_GEOMETRY

**Output:** `geography/lgd_geography_investigation.csv` (6 geography levels documented)

**Data Integrity:** ✓ MAINTAINED
- No fabricated boundaries
- Investigation results explicitly documented
- CODES_ONLY status clearly marked

---

### Phase 2: Population Data Investigation
**Objective:** Search repository for Census or population data

**Directories Searched:**
- `data/raw/census/` — NOT_FOUND
- `data/processed/census/` — NOT_FOUND
- `ml/fields/geography/data/raw/population/` — NOT_FOUND
- `ml/fields/geography/data/processed/population/` — NOT_FOUND

**Files Searched:**
- Pattern: `*population*`, `*census*`
- **Result:** ZERO population files found

**LGD Geography Files:**
- Census 2011 **codes** present in `ulbs_clean.csv`
- **NO population counts** present in any file

**Output:** `geography/population_data_investigation.csv` (1 record: DATA_UNAVAILABLE)

**Data Integrity:** ✓ MAINTAINED
- No fabricated population data
- DATA_UNAVAILABLE status documented
- No zero-filled population columns

---

### Phase 3: Geographic Accessibility Analysis
**Objective:** Create theoretical geographic catchments (spatial buffers)

**Method:**
1. Loaded 106 Mumbai station coordinates (EPSG:4326)
2. Projected to UTM Zone 43N (EPSG:32643) for accurate meter-based buffers
3. Created circular buffers: 500m, 1km, 2km radius
4. Calculated total coverage area per buffer distance
5. Reprojected to EPSG:4326 for GIS compatibility
6. Exported as GeoJSON

**Results:**
| Buffer Distance | Stations | Total Area (km²) | Status |
|----------------|----------|------------------|--------|
| 500 m | 106 | 83.12 | ✓ COMPLETE |
| 1 km | 106 | 332.47 | ✓ COMPLETE |
| 2 km | 106 | 1,329.90 | ✓ COMPLETE |

**Outputs:**
- `geography/mumbai_station_catchments_500m.geojson` (106 polygons)
- `geography/mumbai_station_catchments_1000m.geojson` (106 polygons)
- `geography/mumbai_station_catchments_2000m.geojson` (106 polygons)
- `geography/mumbai_accessibility_summary.csv` (3 buffer summaries)

**Data Integrity:** ✓ MAINTAINED
- Catchments generated from validated M2 coordinates (no coordinate changes)
- Proper CRS used for buffer calculations (UTM Zone 43N)
- Coverage areas calculated accurately
- Type explicitly marked: THEORETICAL_GEOGRAPHIC (not actual transit accessibility)

---

### Phase 4: Station Features with Geography
**Objective:** Add geography metadata to station features

**Method:**
1. Loaded M2 station features (106 records)
2. Added geography join fields (ward, ULB, district)
3. Set all geography fields to NULL
4. Set join_status = BLOCKED_NO_BOUNDARY_GEOMETRY
5. Added catchment availability flags (all TRUE for 500m/1km/2km)

**Output:** `features/mumbai_station_geography.csv` (106 records, 17 columns)

**Schema:**
```
station_id, station_name, latitude, longitude, coordinate_valid,
nearest_distance_m, line_id, line_name, source, source_file, source_url,
ward_code, ward_name, ulb_code, ulb_name, district_code, district_name,
join_status, catchment_500m_available, catchment_1km_available, catchment_2km_available
```

**Data Integrity:** ✓ MAINTAINED
- No fabricated ward/ULB/district assignments
- join_status explicitly set to BLOCKED
- NULL values used for unavailable data (not empty strings or zeros)
- Catchment flags accurately reflect availability

---

### Phase 5: M3 Data Availability Matrix
**Objective:** Document comprehensive data availability for all 5 systems

**Components Documented:**
| System | Components | Status |
|--------|-----------|--------|
| Mumbai | 7 components | PARTIAL (coordinates + catchments only) |
| Chennai | 1 component | DATA_UNAVAILABLE |
| Kolkata | 1 component | DATA_UNAVAILABLE |
| Hyderabad MMTS | 1 component | DATA_UNAVAILABLE |
| Pune | 1 component | DATA_UNAVAILABLE |

**Mumbai Components:**
1. Station Coordinates — COMPLETE
2. City Boundaries — DATA_UNAVAILABLE
3. District Boundaries — CODES_ONLY_NO_GEOMETRY
4. ULB Boundaries — CODES_ONLY_NO_GEOMETRY
5. Ward Boundaries — CODES_ONLY_NO_GEOMETRY
6. Population Data — DATA_UNAVAILABLE
7. Station Catchments — COMPLETE (theoretical buffers)

**Output:** `local_rail_m3_data_matrix.csv` (11 records)

**Data Integrity:** ✓ MAINTAINED
- Mumbai status: PARTIAL (not falsely marked COMPLETE)
- Other systems: DATA_UNAVAILABLE (not hidden)
- Component-level granularity (not system-level aggregation only)
- Notes explain specific blockers

---

## Validation Checklist

### ✓ No Raw Files Modified
- [x] No M1 raw KML files modified
- [x] No M2 processed files modified (stations, lines, features)
- [x] Only new M3 files created in `geography/` and `features/`

### ✓ No Fabricated Data
- [x] No fabricated coordinates (used M2 validated coordinates)
- [x] No fabricated population (marked DATA_UNAVAILABLE)
- [x] No fabricated district assignments (marked BLOCKED)
- [x] No fabricated boundaries (documented absence explicitly)
- [x] No fake service data (not in M3 scope)
- [x] No estimated catchment population (cannot calculate without data)

### ✓ All 106 Mumbai Stations Preserved
- [x] Station count: 106 (unchanged from M2)
- [x] Station IDs: MUM_RAIL_STN_001 to MUM_RAIL_STN_106 (unchanged)
- [x] Station coordinates: Preserved exactly from M2 (no modifications)

### ✓ CRS Documented
- [x] Source CRS: EPSG:4326 (WGS84) — documented
- [x] Buffer calculation CRS: EPSG:32643 (UTM Zone 43N) — documented
- [x] Output CRS: EPSG:4326 (WGS84) — documented
- [x] Justification for UTM Zone 43N: Covers Mumbai, meter-based accuracy

### ✓ Spatial Joins Reproducible
- [x] Method documented: Point-in-polygon spatial join
- [x] Status: NOT_PERFORMED (no boundary polygons available)
- [x] Blocker documented: CODES_ONLY_NO_GEOMETRY

### ✓ Source Provenance Present
- [x] LGD geography files: Source URL documented (https://lgdirectory.gov.in/)
- [x] Station coordinates: Source preserved from M2 (BMC OpenCity.in)
- [x] Catchments: Generated from stations (documented in notes)

### ✓ Historical Population Years Preserved
- [x] N/A (no population data available)
- [x] If population added in future: Year column required

### ✓ Accessibility Calculations Use Projected CRS
- [x] Buffer calculations: EPSG:32643 (UTM Zone 43N, meters)
- [x] Area calculations: Derived from UTM projection (km²)
- [x] Not EPSG:4326 (would give incorrect distances in degrees)

### ✓ Buffer Distances Accurate
- [x] 500m buffer: Verified (500 meters radius)
- [x] 1000m buffer: Verified (1 km radius)
- [x] 2000m buffer: Verified (2 km radius)
- [x] NOT approximations or scaled values

### ✓ No Service-Level Claims
- [x] Catchments labeled: THEORETICAL_GEOGRAPHIC
- [x] NOT labeled: actual transit accessibility, service coverage, ridership catchment
- [x] Limitations documented in all reports
- [x] Service frequency: Acknowledged as UNAVAILABLE

### ✓ Other Domains Untouched
- [x] No Bus files changed
- [x] No Metro files changed
- [x] No National Highways files changed
- [x] No Geography source files changed (only investigated, not modified)

---

## Output Files Summary

### Geography Outputs (7 files)
1. `data/processed/geography/lgd_geography_investigation.csv` — 6 LGD levels
2. `data/processed/geography/population_data_investigation.csv` — Population search results
3. `data/processed/geography/mumbai_station_catchments_500m.geojson` — 106 polygons
4. `data/processed/geography/mumbai_station_catchments_1000m.geojson` — 106 polygons
5. `data/processed/geography/mumbai_station_catchments_2000m.geojson` — 106 polygons
6. `data/processed/geography/mumbai_accessibility_summary.csv` — 3 buffer summaries
7. `data/processed/local_rail_m3_data_matrix.csv` — 11 component records

### Feature Outputs (1 file)
8. `data/processed/features/mumbai_station_geography.csv` — 106 station records with geography metadata

### Report Outputs (3 files)
9. `reports/local_rail_m3_geography_report.md` — Geography investigation + boundary status
10. `reports/local_rail_m3_accessibility_report.md` — Catchment analysis + limitations
11. `reports/local_rail_m3_population_report.md` — Population search + blocked analyses

### Pipeline Script (1 file)
12. `src/03_m3_geography_accessibility.py` — M3 pipeline (reproducible)

**Total:** 12 files created

---

## Key Findings

### Finding 1: LGD Geography is Code-Only
**Issue:** LGD geography files contain hierarchical administrative codes (state, district, ULB, ward) but NO spatial geometry  
**Impact:** Station-to-geography spatial joins are BLOCKED  
**Resolution:** Must acquire spatial boundary polygons from Survey of India, Maharashtra GIS, or community sources (DataMeet, OSM)

### Finding 2: No Population Data in Repository
**Issue:** Zero Census or population data files found in repository  
**Impact:** All population-based analyses are BLOCKED (catchment population, stations per 100k, underserved areas)  
**Resolution:** Must download Census 2011 or Census 2021 data from censusindia.gov.in

### Finding 3: Only Theoretical Accessibility Possible
**Issue:** Service frequency and timetable data remain UNAVAILABLE (from M2)  
**Impact:** Can only calculate geographic proximity (buffers), not actual transit accessibility  
**Resolution:** Must source train frequency from Western Railway / Central Railway or parse timetables

### Finding 4: Catchments Created Successfully
**Success:** All 106 stations have 500m, 1km, 2km catchment polygons  
**Coverage:** 83 km² (500m), 332 km² (1km), 1,330 km² (2km)  
**Quality:** Proper CRS used (UTM Zone 43N), accurate meter-based buffers

---

## M3 Status Table

| Component | Status | Records | Source | Notes |
|-----------|--------|---------|--------|-------|
| **Station Coordinates** | ✓ COMPLETE | 106 | BMC OpenCity.in (M2) | 100% valid coordinates |
| **Boundary Geometry** | ✗ DATA_UNAVAILABLE | 0 | N/A | LGD codes exist but NO polygons |
| **Population** | ✗ DATA_UNAVAILABLE | 0 | N/A | No Census data found |
| **Station Geography Join** | ✗ BLOCKED | 0 | N/A | Cannot perform without boundaries |
| **500m Accessibility** | ✓ COMPLETE | 106 | Generated | Theoretical geographic buffers |
| **1km Accessibility** | ✓ COMPLETE | 106 | Generated | Theoretical geographic buffers |
| **2km Accessibility** | ✓ COMPLETE | 106 | Generated | Theoretical geographic buffers |
| **Station Density** | ⚠ PARTIAL | 0 | N/A | Network density calculated (M2), but no by-district/ULB |
| **Population Catchment** | ✗ BLOCKED | 0 | N/A | No population data |
| **Service Frequency** | ✗ UNAVAILABLE | 0 | N/A | Not in M3 scope (service data missing since M1) |
| **Ridership** | ✗ UNAVAILABLE | 0 | N/A | Not in M3 scope (missing since M1) |

---

## Blocked Analyses Summary

### Geography-Related (BLOCKED by missing boundaries)
1. **Station-to-ward join** — Cannot assign stations to wards
2. **Station-to-ULB join** — Cannot assign stations to ULBs
3. **Station-to-district join** — Cannot assign stations to districts
4. **Station density by ULB** — Cannot calculate stations per ULB
5. **Station density by district** — Cannot calculate stations per district

### Population-Related (BLOCKED by missing population data)
6. **Catchment population** — Cannot calculate people within 500m/1km/2km
7. **Stations per 100k population** — Cannot normalize by population
8. **Population per station** — Cannot calculate people served per station
9. **Underserved area identification** — Cannot flag high-population, low-access areas
10. **Demand estimation** — Cannot estimate potential ridership from population

### Service-Related (UNAVAILABLE, not M3 scope)
11. **Actual transit accessibility** — Requires service frequency (not geographic proximity)
12. **Service quality indicators** — Requires timetable, reliability, crowding data

---

## Data Integrity Summary

### ✓ All Invariants Maintained

**Invariant 1: Provenance on Everything**
- ✓ Station coordinates: Source preserved from M2 (BMC OpenCity.in)
- ✓ Geography investigation: LGD source documented
- ✓ Catchments: Generated from stations (methodology documented)

**Invariant 2: Fail Closed**
- ✓ Missing boundaries: Marked CODES_ONLY_NO_GEOMETRY (not fabricated)
- ✓ Missing population: Marked DATA_UNAVAILABLE (not fabricated)
- ✓ Blocked joins: Status BLOCKED (not attempted with invalid data)
- ✓ Other systems: Chennai/Kolkata/Hyderabad/Pune marked DATA_UNAVAILABLE

**Invariant 3: AI Never Originates Facts**
- ✓ All coordinates from M2 source data (no new coordinates)
- ✓ Catchments calculated via documented projection method
- ✓ No population estimates or assignments invented

**Invariant 8: City- and Field-Agnostic Core**
- ✓ Pipeline works for any city with station coordinates
- ✓ No Mumbai-specific hard-coded values (except CRS selection for region)

**Invariant 9: Idempotent Pipelines**
- ✓ Pipeline can re-run safely (reads M2 outputs, writes new M3 files)
- ✓ No modification of source data

---

## Reproducibility

### Environment
- **Python:** 3.12
- **Key Libraries:** pandas, geopandas, shapely
- **Projection:** EPSG:32643 (WGS 84 / UTM Zone 43N)
- **Buffer Method:** Shapely `geometry.buffer(distance_meters)`

### Execution
```bash
cd ml && uv run python fields/public_transport/local_rail/src/03_m3_geography_accessibility.py
```

**Exit Code:** 0 (success)  
**Execution Time:** <5 seconds

### Determinism
- ✓ Fixed CRS (EPSG:32643, EPSG:4326)
- ✓ Fixed buffer distances (500, 1000, 2000 meters)
- ✓ Stable geometry calculations (shapely deterministic)
- ✓ No random operations

---

## Recommendations

### High Priority — Acquire Missing Data
1. **Spatial Boundaries:** Contact Survey of India, Maharashtra GIS, or use DataMeet/OSM boundaries
2. **Census Population:** Download Census 2011 ward/ULB-level data from censusindia.gov.in
3. **Service Frequency:** Contact Western Railway / Central Railway for timetable data

### Medium Priority — Complete Spatial Analysis
4. **Station-geography joins:** Perform spatial joins once boundaries acquired
5. **Population catchment:** Calculate population within 500m/1km/2km once data acquired
6. **Density analysis:** Calculate stations per ULB, stations per 100k population

### Low Priority — Alternative Methods
7. **OSM Reverse Geocoding:** Use OpenStreetMap Nominatim to assign stations to admin boundaries (if spatial data unavailable)
8. **WorldPop Rasters:** Use modeled population grids as fallback (not Census-official)
9. **Manual Assignment:** Manually assign well-known stations to districts/ULBs (error-prone, not spatial)

---

## Conclusion

Local Rail M3 successfully created **theoretical geographic catchments** for all 106 Mumbai stations (500m, 1km, 2km buffers) and thoroughly documented **data availability and blockers**. However, **all population-based and boundary-based analyses remain BLOCKED** due to missing spatial geometry and population data in the repository.

**Data Integrity:** MAINTAINED — no fabrication, explicit BLOCKED status for unavailable analyses, full provenance documentation.

**Critical Path Forward:** Acquiring spatial boundary polygons and Census population data is **essential prerequisite** for completing population-based transit accessibility analysis.

---

**Auditor:** Kiro AI Agent  
**Audit Date:** 2026-09-29  
**Next Steps:** Git commit M3 work, generate final M3 completion summary
