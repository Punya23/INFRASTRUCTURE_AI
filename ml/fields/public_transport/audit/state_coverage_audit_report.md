# STATE × TRANSPORT MODE COVERAGE AUDIT REPORT
**LokDrishti AI / INFRASTRUCTURE_AI Project**

**Report Date:** 2026-09-29  
**Audit Type:** Complete Repository Inventory (Inspection Only — NO New Data Collected)  
**Auditor:** Automated + Manual Repository Analysis  
**Scope:** 4 Target States × 3 Transport Modes = 12 State×Mode Combinations

---

## 1. Executive Summary

This audit comprehensively inspects the INFRASTRUCTURE_AI repository to determine exactly what public transport data exists for Maharashtra, Delhi, Karnataka, and Tamil Nadu across Bus, Metro, and Local Rail transport modes.

**Key Findings:**
- **3 of 12 target state×mode combinations** have substantial data
- **2 of 12** are blocked (data exists but access restricted)
- **7 of 12** have minimal or missing data
- **1 non-target state (Telangana)** has substantial data and should be preserved

**Data Completeness:**
- **Available:** Mumbai Local Rail (M1-M4 complete), Telangana Bus (full GTFS), Telangana Metro (full GTFS)
- **Partial:** Karnataka Metro (stations only), Tamil Nadu Metro (ridership only), Smart Cities fleet (counts only)
- **Blocked:** Delhi Bus + Metro (GTFS exists but CSRF-protected)
- **Missing:** All Maharashtra bus/metro, Karnataka bus, Tamil Nadu bus/local rail, all population/LGD boundaries

**Critical Blockers:**
- No census population data with spatial boundaries for any state
- No LGD polygon geometries for any geography
- CSRF-protected downloads for Delhi Bus + Metro
- No GTFS for major bus operators (BEST Mumbai, BMTC Bengaluru, MTC Chennai)

---

## 2. Target States and Transport Modes

### 2.1 Target States
1. **Maharashtra** (Mumbai, Pune, Nagpur)
2. **Delhi** (Delhi NCT)
3. **Karnataka** (Bengaluru)
4. **Tamil Nadu** (Chennai)

### 2.2 Transport Modes
1. **Bus** (City bus, intercity bus, GTFS static feeds)
2. **Metro** (Rapid transit, GTFS static feeds)
3. **Local Rail** (Suburban rail, commuter rail)

### 2.3 Non-Target States with Data
- **Telangana** (Hyderabad): Substantial bus + metro data already in repository
  - **Status:** PRESERVE (do not delete or ignore)
  - **Rationale:** High-quality full GTFS for both bus and metro

---

## 3. Repository Data Inventory

### 3.1 Directory Structure Inspected
```
ml/fields/public_transport/
├── bus/
│   ├── data/processed/          ✓ 14 CSV files, 2 GeoJSON, 1 validation report
│   ├── reports/                 ✓ 2 reports (source inventory, validation)
│   ├── notebooks/               ✓ EDA notebook
│   └── src/                     ✓ 4 pipeline scripts
├── metro/
│   ├── data/processed/          ✓ 30+ CSV files (Hyderabad GTFS, Bengaluru stations, Chennai ridership)
│   ├── reports/                 ✓ 3 reports (source inventory, EDA, GTFS validation)
│   ├── notebooks/               ✓ EDA notebook
│   └── src/                     ✓ Pipeline scripts
└── local_rail/
    ├── data/processed/          ✓ 23 CSV files (Mumbai M1-M4 complete)
    ├── reports/                 ✓ 21 reports (M1-M4 full documentation)
    ├── notebooks/               (not yet created)
    └── src/                     ✓ 4 pipeline scripts (M1-M4)
```

### 3.2 Raw Data Manifests Inspected
```
data/manifests/
├── bus_smartcities_fleet_csv.yaml       ✓
├── bus_tgsrtc_gtfs.yaml                 ✓
├── bus_tgsrtc_stops_csv.yaml            ✓
├── metro_bengaluru_bmrcl_ridership_csv.yaml   ✓ (misleading name; contains station codes only)
├── metro_bengaluru_stations_kml.yaml    ✓
├── metro_chennai_cmrl_ridership_csv.yaml ✓
└── metro_hyd_hmrl_gtfs.yaml             ✓
```

### 3.3 Files Analyzed (Subset)
- **Bus:** 14 processed CSV files, 2 GeoJSON, 2 reports
- **Metro:** 30+ processed CSV files, 1 GeoJSON, 3 reports
- **Local Rail:** 23 processed CSV files, 21 reports

**Total files inspected:** 80+ data files, 26 reports, 3 source inventories, 4 manifest files

---

## 4. State × Mode Matrix

| State | Bus | Metro | Local Rail |
|-------|-----|-------|------------|
| **Maharashtra** | MINIMAL | MISSING | **SUBSTANTIAL** |
| **Delhi** | BLOCKED | BLOCKED | NOT_APPLICABLE |
| **Karnataka** | MINIMAL | PARTIAL | NOT_APPLICABLE |
| **Tamil Nadu** | MINIMAL | PARTIAL | BLOCKED |
| **Telangana** (other) | **SUBSTANTIAL** | **SUBSTANTIAL** | MISSING |

**Legend:**
- **SUBSTANTIAL:** Data collected, cleaned, validated, analyzed (EDA + geospatial or gap analysis done)
- **PARTIAL:** Some data available but incomplete (e.g., coordinates only, no GTFS; or ridership only, no network)
- **MINIMAL:** Only aggregate counts or metadata; no geographic coordinates or service data
- **BLOCKED:** Data source identified but access blocked (CSRF, PDF-only, manual download required)
- **MISSING:** No data collected; no source identified or source not accessible
- **NOT_APPLICABLE:** Transport mode does not exist in that state/city

---

## 5. Dataset-Level Matrix

See `state_mode_dataset_matrix.csv` for complete 72-row dataset-level breakdown.

**Summary by Dataset Category:**

### A. Basic Infrastructure
| Dataset | Maharashtra | Delhi | Karnataka | Tamil Nadu | Telangana |
|---------|-------------|-------|-----------|------------|-----------|
| **Stations/Stops** | Local Rail: 106 ✓ | BLOCKED | Metro: 63 ✓ | MINIMAL | Bus: 5,028 ✓<br>Metro: 57 ✓ |
| **Routes/Lines** | Local Rail: lines ✓ | BLOCKED | MINIMAL | MINIMAL | Bus: 1,031 ✓<br>Metro: 3 ✓ |
| **Coordinates** | Local Rail: YES | BLOCKED | Metro: YES | MINIMAL | Bus: YES<br>Metro: YES |
| **Network Geometry** | Local Rail: YES | BLOCKED | Metro: YES | MINIMAL | Bus: YES<br>Metro: YES |

### B. Service Data
| Dataset | Maharashtra | Delhi | Karnataka | Tamil Nadu | Telangana |
|---------|-------------|-------|-----------|------------|-----------|
| **Timetable/Trips** | MISSING | BLOCKED | MISSING | BLOCKED | Bus: YES ✓<br>Metro: YES ✓ |
| **Frequency** | MISSING | BLOCKED | MISSING | MISSING | Bus: derivable<br>Metro: derivable |
| **Operating Hours** | MISSING | BLOCKED | MISSING | MISSING | Bus: derivable<br>Metro: derivable |

### C. Usage Data
| Dataset | Maharashtra | Delhi | Karnataka | Tamil Nadu | Telangana |
|---------|-------------|-------|-----------|------------|-----------|
| **Ridership** | MISSING | MISSING | MISSING | Metro: YES ✓ (monthly) | MISSING |
| **Station-level** | MISSING | MISSING | MISSING | MISSING | MISSING |

### D. Commercial Data
| Dataset | Maharashtra | Delhi | Karnataka | Tamil Nadu | Telangana |
|---------|-------------|-------|-----------|------------|-----------|
| **Fare Data** | MISSING | BLOCKED | MISSING | MISSING | Metro: YES ✓ |

### E. Geography
| Dataset | ALL STATES | Status |
|---------|------------|--------|
| **LGD Codes** | PARTIAL | Codes available for some records but incomplete |
| **LGD Boundaries** | **BLOCKED** | Codes exist but NO polygon geometries |
| **Population** | **MISSING** | No census ward-level data with boundaries |
| **Population by Geography** | **MISSING** | Blocked by missing LGD boundaries + population |

### F. Geospatial Analysis
| Dataset | Maharashtra | Delhi | Karnataka | Tamil Nadu | Telangana |
|---------|-------------|-------|-----------|------------|-----------|
| **Catchments** | Local Rail: YES ✓ | NOT_STARTED | NOT_STARTED | NOT_STARTED | Bus: NOT_STARTED<br>Metro: NOT_STARTED |
| **Station Spacing** | Local Rail: YES ✓ | NOT_STARTED | NOT_STARTED | NOT_STARTED | NOT_STARTED |
| **Network Analysis** | Local Rail: YES ✓ | NOT_STARTED | NOT_STARTED | NOT_STARTED | NOT_STARTED |
| **Gap Indicators** | Local Rail: YES ✓ (11 gaps) | NOT_STARTED | NOT_STARTED | NOT_STARTED | NOT_STARTED |

---

## 6. Processing Status

See `state_mode_processing_matrix.csv` for complete processing status.

**Pipeline Stages:**
1. Raw Data Collection
2. Cleaning
3. Validation
4. EDA (Exploratory Data Analysis)
5. Geospatial Analysis
6. LGD Mapping
7. Population Analysis
8. Accessibility Analysis
9. Gap Analysis

**Completion Status:**

### Fully Complete (All Stages):
- **Maharashtra Local Rail (Mumbai Suburban):**
  - M1 (Collection) ✓, M2 (EDA) ✓, M3 (Geography) ✓, M4 (Gap Analysis) ✓
  - 106 stations, 307.46 km network, 11 potential spacing gaps identified
  - Population analysis BLOCKED (no census data)
  - Service analysis BLOCKED (no frequency data)

### Substantial (Data + Cleaning + Validation + EDA + Geospatial):
- **Telangana Bus (TGSRTC):**
  - Full GTFS: 5,028 stops, 1,031 routes, trips, stop_times, calendar
  - Cleaning ✓, Validation ✓, EDA ✓, Geospatial ✓ (stop coordinates, route geometry)
  - LGD mapping PARTIAL, catchment analysis NOT_STARTED

- **Telangana Metro (Hyderabad HMRL):**
  - Full GTFS: 57 stations, 3 lines, 2,820 trips, shapes, fares
  - Cleaning ✓, Validation ✓, EDA ✓
  - Geospatial NOT_STARTED, LGD mapping NOT_STARTED

### Partial (Data + Cleaning + EDA):
- **Karnataka Metro (Bengaluru):** 63 stations with coordinates, no GTFS
- **Tamil Nadu Metro (Chennai):** 39 months ridership, no station/network data

### Minimal (Smart Cities Fleet Only):
- Maharashtra Bus (Pune, Nagpur): fleet counts only
- Karnataka Bus (Bengaluru): fleet counts only
- Tamil Nadu Bus (Chennai): fleet counts only

### Blocked:
- Delhi Bus: GTFS exists but CSRF-protected
- Delhi Metro: GTFS exists but CSRF-protected
- Tamil Nadu Local Rail: Timetable in PDF/HTML only

### Missing:
- Maharashtra Bus (MSRTC, BEST, PMPML): No GTFS collected
- Maharashtra Metro (Mumbai, Pune, Nagpur): No data collected
- Karnataka Bus (BMTC): No GTFS collected
- Tamil Nadu Bus (MTC): No GTFS collected
- Telangana Local Rail (MMTS): No data collected

---

## 7. Available Data (Detailed)

### 7.1 Maharashtra
**Local Rail (Mumbai Suburban):**
- **Status:** M1-M4 COMPLETE
- **Records:** 106 stations, 307.46 km network
- **Coordinates:** YES (all valid)
- **Network Geometry:** YES (line KML)
- **Processing:**
  - M1 (Collection) ✓: Stations + lines from BMC OpenCity
  - M2 (EDA + Network) ✓: Spacing analysis (median 1,759m), network metrics
  - M3 (Geography) ✓: Catchments (500m/1km/2km), LGD codes (no boundaries)
  - M4 (Gap Analysis) ✓: 11 potential spacing gaps (P90/P95 thresholds)
- **Limitations:** No population, no service frequency, no ridership
- **Source:** BMC via OpenCity.in (Public Domain)

**Bus:**
- **Status:** MINIMAL (fleet counts only)
- **Records:** Pune (2 records), Nagpur (1 record)
- **Data:** Bus counts, terminal/stand/stop counts — NO coordinates
- **Source:** MoHUA Smart Cities via OpenCity.in

**Metro:**
- **Status:** MISSING
- **Mumbai/Pune/Nagpur:** No station coordinates, no GTFS collected

### 7.2 Delhi
**Bus + Metro:**
- **Status:** BLOCKED
- **Source:** Delhi OTD (Open Transit Data) portal
  - Bus: https://otd.delhi.gov.in/data/staticDTC/
  - Metro: https://otd.delhi.gov.in/data/staticDMRC/
- **Blocking Issue:** CSRF-protected form download (cannot automate via GET)
- **Estimated Data:** Bus GTFS available, Metro ~262 stations + ~36 routes available
- **Action Required:** Manual download via browser

**Local Rail:**
- **Status:** NOT_APPLICABLE (Delhi does not have suburban rail system)

### 7.3 Karnataka
**Metro (Bengaluru):**
- **Status:** PARTIAL (stations only, no GTFS)
- **Records:** 63 stations with coordinates
- **Coordinates:** YES (from KML)
- **Network Geometry:** YES (lines in KML)
- **GTFS:** MISSING (no routes, trips, stop_times, frequencies)
- **Ridership:** File labeled "ridership" contains only station codes/names (NO actual ridership values)
- **Processing:** Cleaning ✓, Validation ✓, EDA ✓
- **Source:** BMRCL via OpenCity.in

**Bus:**
- **Status:** MINIMAL (fleet counts only)
- **Records:** Bengaluru (2 records: 850 AC, 5,827 Non-AC buses)
- **Data:** Bus counts, terminal/stand/stop counts — NO coordinates
- **Source:** MoHUA Smart Cities via OpenCity.in

**Local Rail:**
- **Status:** NOT_APPLICABLE (Bengaluru does not currently have suburban rail)

### 7.4 Tamil Nadu
**Metro (Chennai):**
- **Status:** PARTIAL (ridership only, no network data)
- **Records:** 39 monthly ridership records (Apr 2023 – Jun 2026)
- **Data:** System-wide monthly ridership by ticket type (Closed Loop, QR, NCMC)
  - Total: 345.3 million passengers
  - Average monthly: 8.9 million passengers
  - Peak monthly: 10.5 million passengers
- **Missing:** Station coordinates, routes, GTFS
- **Processing:** Cleaning ✓, Validation ✓, EDA ✓
- **Source:** CMRL via OpenCity.in

**Bus:**
- **Status:** MINIMAL (fleet counts only)
- **Records:** Chennai (2 records: 3,740 buses)
- **Data:** Bus counts, terminal/stand/stop counts — NO coordinates
- **Source:** MoHUA Smart Cities via OpenCity.in

**Local Rail (Chennai Suburban):**
- **Status:** BLOCKED (timetable exists but PDF/HTML only)
- **Source:** Southern Railway (https://sr.indianrailways.gov.in/)
- **Blocking Issue:** Timetable in PDF/HTML format, not machine-readable GTFS
- **Action Required:** Manual station extraction OR find alternate source

### 7.5 Telangana (Non-Target State)
**Bus (TGSRTC):**
- **Status:** SUBSTANTIAL (full GTFS)
- **Records:** 1 agency, 5,028 stops, 1,031 routes, full trips/stop_times/calendar
- **Coordinates:** YES (all stops geocoded)
- **Network Geometry:** YES (route geometry derived from stop sequences)
- **Processing:** Collection ✓, Cleaning ✓, Validation ✓, EDA ✓, Geospatial ✓
- **GeoJSON:** bus_stops.geojson, bus_routes.geojson created
- **LGD Mapping:** PARTIAL
- **Source:** TGSRTC via OpenCity.in

**Metro (Hyderabad HMRL):**
- **Status:** SUBSTANTIAL (full GTFS)
- **Records:** 1 agency, 57 stations (117 platforms), 3 routes, 2,820 trips, 61,236 stop_times, 2,450 shape points, 10 fare zones, 3,249 fare rules
- **Coordinates:** YES (all stations geocoded)
- **Network Geometry:** YES (shapes with 6 linestrings)
- **Fare Data:** YES (fare_attributes + fare_rules)
- **Processing:** Collection ✓, Cleaning ✓, Validation ✓, EDA ✓
- **Source:** HMRL via OpenCity.in

**Local Rail (MMTS):**
- **Status:** MISSING
- **Source:** No machine-readable data found (third-party timetable aggregator exists but not authoritative)

---

## 8. Partial Data

### 8.1 Geographic Data Available, Service Data Missing
- **Karnataka Metro (Bengaluru):** 63 stations with coordinates, NO GTFS
- **Maharashtra Local Rail (Pune Suburban):** No data (only PDF DPR for Pune Metro exists)

### 8.2 Ridership Available, Network Data Missing
- **Tamil Nadu Metro (Chennai):** 39 months ridership, NO station coordinates or GTFS

### 8.3 Fleet Counts Only, No Geographic Data
- **Smart Cities Bus Fleet (37 cities):** Bus/terminal/stop counts, NO stop coordinates
  - Maharashtra: Pune, Nagpur
  - Karnataka: Bengaluru
  - Tamil Nadu: Chennai
  - 33 other cities (not in target states)

### 8.4 Codes Available, Geometries Missing
- **LGD Codes:** Partial mapping exists for some datasets but NO polygon geometries for any geography

---

## 9. Missing Data

### 9.1 Major Bus Operators (No GTFS Collected)
- **MSRTC** (Maharashtra State RTC): State-wide intercity
- **BEST** (Mumbai): City bus network
- **PMPML** (Pune): City bus network
- **BMTC** (Bengaluru): City bus network
- **MTC** (Chennai): City bus network

### 9.2 Metro Systems (No Data Collected)
- **Mumbai Metro** (MMRDA/MML): No stations, no GTFS
- **Pune Metro:** No stations, no GTFS (only PDF DPR)
- **Nagpur Metro** (MahaMetro): No stations, no GTFS
- **Chennai Metro** (CMRL): No stations, no GTFS (only ridership)

### 9.3 Local Rail Systems (No Data Collected)
- **Pune Suburban** (Pune-Lonavala EMU): No stations, no timetable
- **Telangana MMTS** (Hyderabad): No stations, no timetable

### 9.4 Service Data (All Systems)
- **Service Frequency:** Only derivable from Telangana GTFS; missing for all other systems
- **Ridership (Station-Level):** MISSING for all systems (only Chennai has system-wide monthly)
- **Operating Hours:** Only derivable from Telangana GTFS; missing for all other systems

### 9.5 Geographic Data (All Systems)
- **Population Data:** NO census ward-level population with spatial boundaries for ANY state
- **LGD Boundaries:** LGD codes exist but NO polygon geometries for ANY geography

---

## 10. Blocked Data

### 10.1 CSRF-Protected Downloads
- **Delhi Bus (DTC):** Full GTFS available at https://otd.delhi.gov.in/data/staticDTC/
  - **Blocking Issue:** Form-based download with CSRF token
  - **Action:** Manual download via browser
  - **Priority:** HIGH (unblocks entire Delhi bus network)

- **Delhi Metro (DMRC):** Full GTFS available at https://otd.delhi.gov.in/data/staticDMRC/
  - **Blocking Issue:** Form-based download with CSRF token
  - **Estimated Data:** ~262 stations, ~36 routes, full GTFS
  - **Action:** Manual download via browser
  - **Priority:** HIGH (unblocks entire Delhi metro network)

### 10.2 PDF/HTML Only (Not Machine-Readable)
- **Chennai Suburban Rail:** Timetable at https://sr.indianrailways.gov.in/
  - **Blocking Issue:** PDF/HTML format, not GTFS
  - **Action:** Manual station extraction OR find alternate source
  - **Priority:** MEDIUM

- **Pune Metro:** DPR document at https://data.opencity.in/dataset/pune-metro-detailed-project-report
  - **Blocking Issue:** PDF only, no KML/CSV/GTFS
  - **Action:** Extract station info from PDF OR find KML/CSV
  - **Priority:** LOW

### 10.3 Missing Spatial Boundaries
- **LGD Boundaries:** LGD codes available but NO polygon geometries
  - **Source:** https://lgdirectory.gov.in/ (codes only)
  - **Blocking Issue:** No downloadable spatial boundary files found
  - **Action:** Collect LGD ward/ULB boundaries (DataMeet, Survey of India, or alternate)
  - **Priority:** HIGH (blocks all LGD-based analyses)

- **Census Population:** No ward-level population with boundaries
  - **Source:** Census 2021 (check availability of digital spatial data)
  - **Blocking Issue:** No spatial population data found
  - **Action:** Collect Census 2021 OR use WorldPop/GHSL raster
  - **Priority:** HIGH (blocks all population-based analyses)

---

## 11. Geospatial Readiness

### 11.1 Ready for Geospatial Analysis (Coordinates Available)
- **Maharashtra Local Rail (Mumbai Suburban):** ✓ COMPLETE (catchments, spacing, gap analysis done)
- **Telangana Bus (TGSRTC):** ✓ READY (5,028 stops geocoded; catchments not yet generated)
- **Telangana Metro (Hyderabad):** ✓ READY (57 stations geocoded; catchments not yet generated)
- **Karnataka Metro (Bengaluru):** ✓ READY (63 stations geocoded; catchments not yet generated)

### 11.2 Blocked (Missing Coordinates)
- All Maharashtra bus systems
- All Maharashtra metro systems (Mumbai, Pune, Nagpur)
- All Karnataka bus systems
- All Tamil Nadu bus systems
- All Tamil Nadu metro systems (Chennai — ridership exists but no station coordinates)
- All Tamil Nadu local rail systems (Chennai Suburban)
- Delhi bus + metro (GTFS exists but not downloaded)

---

## 12. LGD Readiness

### 12.1 LGD Codes Available (Partial)
- **Maharashtra Local Rail (Mumbai):** LGD codes exist but NO boundaries
- **Telangana Bus (TGSRTC):** Partial LGD mapping

### 12.2 LGD Codes Missing
- All metro systems
- Most bus systems

### 12.3 LGD Boundaries Missing (BLOCKED for ALL)
- **No polygon geometries exist for ANY geography**
- LGD codes available but cannot perform spatial joins without boundaries
- **Action:** Collect LGD ward/ULB boundaries from DataMeet, Survey of India, or alternate source

---

## 13. Population Readiness

### 13.1 Status: MISSING for ALL Systems
- **No census ward-level population data with spatial boundaries**
- **Cannot calculate:**
  - Population per station/stop
  - Stations per 100k population
  - Population within catchments
  - Underserved area identification
  - Demand-based gap prioritization

### 13.2 Fallback Options
- **WorldPop:** 1km raster data (lower resolution than ward-level)
- **GHSL Population Grid:** 1km raster (already downloaded for other purposes)
- **Estimate from Built-Up Area:** GHSL built-up × density assumptions (high uncertainty)

### 13.3 Action Required
- Collect Census 2021 ward-level population + spatial boundaries (preferred)
- OR use WorldPop 1km raster (fallback)

---

## 14. Ridership Readiness

### 14.1 Ridership Available
- **Tamil Nadu Metro (Chennai):** System-wide monthly ridership ✓ (39 months, by ticket type)
  - **Note:** NOT station-level; cannot identify high-demand stations

### 14.2 Ridership Missing
- All Maharashtra systems (bus, metro, local rail)
- All Delhi systems
- All Karnataka systems
- Telangana bus (TGSRTC)
- Telangana metro (Hyderabad)
- All local rail systems

### 14.3 Ridership Estimation (Fallback)
- **From Service Frequency × Capacity:**
  - Formula: ridership ≈ trains/hour × capacity/train × operating hours
  - High uncertainty; load factor varies
  - Only feasible if service frequency data available

---

## 15. Frequency/Service Readiness

### 15.1 Service Frequency Derivable
- **Telangana Bus (TGSRTC):** GTFS stop_times → calculate trains/hour
- **Telangana Metro (Hyderabad):** GTFS stop_times → calculate trains/hour

### 15.2 Service Frequency Missing
- Maharashtra Local Rail (Mumbai): No MRVC service frequency data
- All Maharashtra bus/metro
- All Delhi systems (GTFS exists but not downloaded)
- All Karnataka systems
- All Tamil Nadu systems

### 15.3 Action Required
- Derive frequency from Telangana GTFS stop_times
- Collect MRVC service frequency for Mumbai Suburban
- Manual download Delhi GTFS (unblocks Delhi frequency calculation)
- Collect service frequency for other systems

---

## 16. Remaining Work

See `state_mode_remaining_work.csv` for complete 45-row priority list.

**Summary by Priority:**

### HIGH PRIORITY (Unblocks Major Systems or Analyses)
1. **Population Data:** Census 2021 ward-level + boundaries OR WorldPop raster
   - **Impact:** Unblocks 6 population indicators for all systems
2. **Mumbai Suburban Service Frequency:** MRVC trains/hour per station
   - **Impact:** Unblocks 3 service indicators for Mumbai M4
3. **Delhi Bus + Metro GTFS:** Manual download from Delhi OTD
   - **Impact:** Unblocks 2 entire state×mode combinations
4. **BEST (Mumbai) Bus GTFS:** Collect from BEST
   - **Impact:** Unblocks Mumbai bus network
5. **BMTC (Bengaluru) Bus GTFS:** Collect from BMTC
   - **Impact:** Unblocks Bengaluru bus network
6. **Chennai Metro Stations:** Collect CMRL station coordinates
   - **Impact:** Unblocks Chennai metro network analysis
7. **Chennai Suburban Stations:** Extract from timetable OR find alternate source
   - **Impact:** Unblocks Chennai local rail network

### MEDIUM PRIORITY (Complete Partial Datasets)
8. **Mumbai Suburban Ridership:** Collect MRVC station-level ridership
9. **MSRTC GTFS:** Collect Maharashtra State RTC GTFS
10. **PMPML (Pune) Bus GTFS:** Collect from PMPML
11. **Mumbai/Pune/Nagpur Metro Data:** Collect station coordinates + GTFS
12. **Bengaluru Metro GTFS:** Collect BMRCL GTFS (stations already exist)
13. **Bengaluru Metro Ridership:** Collect actual BMRCL ridership values
14. **MTC (Chennai) Bus GTFS:** Collect from MTC
15. **Chennai Metro GTFS:** Collect CMRL GTFS
16. **TGSRTC/HMRL Ridership:** Identify and collect ridership sources
17. **Hyderabad MMTS Data:** Collect MMTS station coordinates + timetable

### LOW PRIORITY (Small Systems or Enhancements)
18. **LGD Spatial Boundaries:** Collect ward/ULB polygons for all geographies
19. **Telangana Bus LGD Mapping:** Complete LGD mapping for all 5,028 stops
20. **Telangana Bus/Metro Catchment Analysis:** Generate 500m/1km/2km buffers
21. **Telangana Metro Gap Analysis:** Perform spacing/network gap analysis
22. **Bengaluru Metro Catchment/Gap Analysis:** Perform geospatial + gap analysis
23. **Nagpur Bus/Metro Data:** Collect Nagpur bus operator + MahaMetro data
24. **Pune Suburban Rail:** Collect Pune-Lonavala EMU data

**Total Remaining Datasets:** 45+ datasets across data collection, cleaning, validation, EDA, geospatial, LGD, population, accessibility, and gap analysis

---

## 17. Recommended Data Collection Order

### Phase 1: Unblock Existing Partial Datasets (Highest ROI)
1. **Manual Download Delhi Bus + Metro GTFS** (2 state×mode combinations)
2. **Collect Mumbai Suburban Service Frequency + Ridership** (unblocks M4 indicators)
3. **Collect Chennai Metro Stations** (unblocks network analysis for existing ridership data)
4. **Collect Population Data** (unblocks population analysis for Mumbai + Telangana)
5. **Collect LGD Boundaries** (unblocks LGD integration for all systems)

### Phase 2: Major City Bus Networks (Large Urban Areas)
6. **Collect BEST (Mumbai) Bus GTFS**
7. **Collect BMTC (Bengaluru) Bus GTFS**
8. **Collect MTC (Chennai) Bus GTFS**
9. **Collect PMPML (Pune) Bus GTFS**

### Phase 3: Metro Networks (Complete State Coverage)
10. **Collect Mumbai Metro GTFS** (MMRDA/MML)
11. **Collect Pune Metro Stations + GTFS**
12. **Collect Bengaluru Metro GTFS** (stations already exist)
13. **Collect Chennai Metro GTFS** (ridership already exists)
14. **Collect Nagpur Metro GTFS** (MahaMetro)

### Phase 4: Local Rail Systems
15. **Collect Chennai Suburban Rail Stations + Timetable**
16. **Collect Pune Suburban Rail Data**
17. **Collect Hyderabad MMTS Data**

### Phase 5: State-Level Bus Operators
18. **Collect MSRTC GTFS** (Maharashtra State)
19. **Collect KSRTC GTFS** (Karnataka State) — if applicable

### Phase 6: Geospatial Processing for Existing Data
20. **Generate Catchments:** Telangana Bus (5,028 stops), Telangana Metro (57 stations), Bengaluru Metro (63 stations)
21. **Perform Gap Analysis:** Telangana Bus, Telangana Metro, Bengaluru Metro
22. **Complete LGD Mapping:** Telangana Bus, other systems

---

## 18. Data Quality Risks

### 18.1 Coordinate Quality Risks
- **Mumbai Local Rail:** 100% valid coordinates (verified in M2)
- **Telangana Bus:** 100% valid coordinates (verified)
- **Telangana Metro:** Coordinates from GTFS (not yet validated with ground truth)
- **Bengaluru Metro:** Coordinates from KML (not yet validated)
- **Smart Cities Fleet:** NO coordinates (aggregate counts only)

### 18.2 GTFS Quality Risks
- **Telangana Bus (TGSRTC):** High referential integrity (validated)
- **Telangana Metro (Hyderabad):** High referential integrity (validated)
- **Delhi Bus/Metro:** Not yet downloaded; quality unknown
- **Other systems:** No GTFS collected

### 18.3 Ridership Data Risks
- **Chennai Metro:** System-wide monthly totals; NO station-level breakdown
- **Bengaluru Metro:** File labeled "ridership" contains NO ridership values (only station codes)
- **All other systems:** No ridership data

### 18.4 Population Data Risks
- **Census 2021:** May not be available as digital spatial data
- **WorldPop/GHSL:** 1km resolution (coarser than ward-level)
- **Estimation from Built-Up:** High uncertainty

### 18.5 LGD Boundary Risks
- **LGD Portal:** Codes available but no downloadable spatial files found
- **DataMeet:** Community-curated; may have gaps or quality issues
- **Survey of India:** Official but may not be freely available

---

## 19. Repository Safety Audit

### 19.1 Unchanged Files (Verified)
✅ **National Highways:** No files modified (as required)
✅ **Existing Bus/Metro/Local Rail Data:** No raw or processed files modified
✅ **Existing Reports:** No reports modified or deleted
✅ **Existing Pipelines:** No scripts modified

### 19.2 New Files Created (Audit Outputs)
✅ `audit/state_mode_dataset_matrix.csv` (72 rows)
✅ `audit/state_mode_processing_matrix.csv` (13 rows)
✅ `audit/state_mode_remaining_work.csv` (45 rows)
✅ `audit/state_mode_available_data_summary.md`
✅ `audit/state_coverage_audit_report.md` (this document)

### 19.3 Git Working Tree Status
✅ No uncommitted changes to existing data files
✅ Only new audit files created
✅ No deletions
✅ No modifications to existing datasets

---

## 20. Current Project State (Final Answers)

### Q1: Which of the four target states currently have BUS data?
- **Maharashtra:** MINIMAL (Smart Cities fleet counts only; no GTFS)
- **Delhi:** BLOCKED (GTFS exists but CSRF-protected download)
- **Karnataka:** MINIMAL (Smart Cities fleet counts only; no GTFS)
- **Tamil Nadu:** MINIMAL (Smart Cities fleet counts only; no GTFS)
- **Telangana (non-target):** SUBSTANTIAL (Full TGSRTC GTFS: 5,028 stops, 1,031 routes)

### Q2: Which have METRO data?
- **Maharashtra:** MISSING (no Mumbai/Pune/Nagpur Metro data)
- **Delhi:** BLOCKED (GTFS exists but CSRF-protected download)
- **Karnataka:** PARTIAL (Bengaluru: 63 stations, no GTFS)
- **Tamil Nadu:** PARTIAL (Chennai: ridership only, no stations/GTFS)
- **Telangana (non-target):** SUBSTANTIAL (Hyderabad full GTFS: 57 stations, 3 lines)

### Q3: Which have LOCAL RAIL data?
- **Maharashtra:** SUBSTANTIAL (Mumbai Suburban M1-M4 complete: 106 stations, 307.46 km)
- **Delhi:** NOT_APPLICABLE (no suburban rail system)
- **Karnataka:** NOT_APPLICABLE (no suburban rail system)
- **Tamil Nadu:** BLOCKED (Chennai timetable exists but PDF/HTML only)
- **Telangana (non-target):** MISSING (Hyderabad MMTS — no data)

### Q4: Which state + mode combinations are complete?
- **Maharashtra Local Rail (Mumbai Suburban):** M1-M4 complete (population/service/ridership blocked)

### Q5: Which are partial?
- **Karnataka Metro (Bengaluru):** Stations only, no GTFS
- **Tamil Nadu Metro (Chennai):** Ridership only, no stations/GTFS
- **Telangana Bus (TGSRTC):** Data + cleaning + EDA + geospatial ✓; catchments/gap analysis not done
- **Telangana Metro (Hyderabad):** Data + cleaning + EDA ✓; geospatial/gap analysis not done

### Q6: Which are missing?
- All Maharashtra bus/metro (except Mumbai Local Rail)
- Karnataka bus
- Tamil Nadu bus
- Tamil Nadu metro stations/GTFS
- Tamil Nadu local rail
- Telangana local rail

### Q7: Which are blocked?
- Delhi bus (GTFS exists but CSRF-protected)
- Delhi metro (GTFS exists but CSRF-protected)
- Chennai suburban rail (timetable exists but PDF only)

### Q8: Which datasets are already cleaned?
- Maharashtra Local Rail (Mumbai): ✓
- Telangana Bus (TGSRTC): ✓
- Telangana Metro (Hyderabad): ✓
- Karnataka Metro (Bengaluru): ✓
- Tamil Nadu Metro (Chennai ridership): ✓
- Smart Cities bus fleet (all cities): ✓

### Q9: Which datasets already have EDA?
- Maharashtra Local Rail (Mumbai): ✓ (M2 complete)
- Telangana Bus (TGSRTC): ✓
- Telangana Metro (Hyderabad): ✓
- Karnataka Metro (Bengaluru): ✓
- Tamil Nadu Metro (Chennai ridership): ✓
- Smart Cities bus fleet: ✓

### Q10: Which datasets already have geospatial analysis?
- Maharashtra Local Rail (Mumbai): ✓ (M3 complete: catchments, spacing, network analysis)
- Telangana Bus (TGSRTC): ✓ (stop coordinates, route geometry; catchments not yet generated)

### Q11: Which datasets still need LGD integration?
- Maharashtra Local Rail (Mumbai): BLOCKED (LGD codes exist, no boundaries)
- Telangana Bus (TGSRTC): PARTIAL (some mapping done, incomplete)
- Telangana Metro (Hyderabad): NOT_STARTED
- Karnataka Metro (Bengaluru): NOT_STARTED
- All other systems: NOT_STARTED or BLOCKED

### Q12: Which datasets still need population?
- **ALL SYSTEMS:** Population data missing for all states

### Q13: Which datasets still need frequency?
- Maharashtra Local Rail (Mumbai): MISSING (no MRVC service frequency)
- Telangana Bus (TGSRTC): DERIVABLE (from GTFS stop_times)
- Telangana Metro (Hyderabad): DERIVABLE (from GTFS stop_times)
- All other systems: MISSING or BLOCKED

### Q14: Which datasets still need ridership?
- Maharashtra Local Rail (Mumbai): MISSING
- Telangana Bus (TGSRTC): MISSING
- Telangana Metro (Hyderabad): MISSING
- Karnataka Metro (Bengaluru): MISSING (file labeled ridership has no values)
- Tamil Nadu Metro (Chennai): AVAILABLE (system-wide monthly; not station-level)
- All other systems: MISSING or BLOCKED

### Q15: Which datasets still need gap analysis?
- Telangana Bus (TGSRTC): NOT_STARTED
- Telangana Metro (Hyderabad): NOT_STARTED
- Karnataka Metro (Bengaluru): NOT_STARTED
- All other systems with data: NOT_STARTED

### Q16: What are the exact remaining datasets we need to collect?
See `state_mode_remaining_work.csv` for complete 45-row list. **Top priorities:**
1. Census 2021 population + boundaries OR WorldPop raster
2. Mumbai Suburban service frequency (MRVC)
3. Delhi Bus + Metro GTFS (manual download)
4. BEST (Mumbai) Bus GTFS
5. BMTC (Bengaluru) Bus GTFS
6. Chennai Metro stations
7. Chennai Suburban Rail stations
8. LGD spatial boundaries
9. Mumbai/Pune/Nagpur Metro data
10. PMPML (Pune) Bus GTFS
11. MTC (Chennai) Bus GTFS
12. Ridership data for all systems

### Q17: Which missing datasets are blockers for final integrated Public Transport analysis?
**Critical Blockers:**
1. **Population data:** Blocks all population-based analyses (underserved areas, demand prioritization)
2. **LGD boundaries:** Blocks administrative mapping and jurisdiction analysis
3. **Service frequency:** Blocks effective accessibility and service quality assessment
4. **Bus GTFS for major cities:** Blocks urban bus network analysis for Mumbai, Bengaluru, Chennai

**High Priority (Unblocks Major Systems):**
5. **Delhi Bus + Metro GTFS:** Blocks entire Delhi state
6. **Chennai Metro stations:** Blocks network analysis despite having ridership data
7. **Chennai Suburban Rail stations:** Blocks Tamil Nadu local rail analysis

---

## 21. Next Data Collection Priority

### Tier 1: Unblock Existing Analyses (Highest ROI)
1. **Manual download Delhi Bus + Metro GTFS** → Unblocks 2 state×mode combinations
2. **Collect population data (Census 2021 or WorldPop)** → Unblocks 6 indicators for all systems
3. **Collect Mumbai Suburban service frequency** → Unblocks 3 service indicators for M4
4. **Collect Chennai Metro stations** → Unblocks network analysis for existing ridership
5. **Collect LGD spatial boundaries** → Unblocks administrative mapping for all systems

### Tier 2: Major City Bus Networks (Large Impact)
6. **BEST (Mumbai) Bus GTFS** → Largest city in Maharashtra
7. **BMTC (Bengaluru) Bus GTFS** → Largest city in Karnataka
8. **MTC (Chennai) Bus GTFS** → Largest city in Tamil Nadu

### Tier 3: Complete Metro Coverage
9. **Mumbai Metro (MMRDA/MML) GTFS** → Complete Maharashtra metro
10. **Bengaluru Metro (BMRCL) GTFS** → Stations exist; need service data
11. **Chennai Metro (CMRL) GTFS** → Ridership exists; need network data
12. **Pune Metro GTFS** → Complete Maharashtra metro
13. **Nagpur Metro (MahaMetro) GTFS** → Complete Maharashtra metro

### Tier 4: Local Rail Systems
14. **Chennai Suburban Rail stations + timetable** → Extract from Southern Railway OR alternate source
15. **Pune Suburban Rail data** → Pune-Lonavala EMU
16. **Hyderabad MMTS data** → Complete Telangana transport coverage

### Tier 5: Geospatial Processing for Existing Data
17. **Generate catchments for Telangana Bus (5,028 stops)**
18. **Generate catchments for Telangana Metro (57 stations)**
19. **Generate catchments for Bengaluru Metro (63 stations)**
20. **Perform gap analysis for Telangana Bus, Telangana Metro, Bengaluru Metro**

---

## 22. Summary

**Audit Completion:** ✅ COMPLETE

**State×Mode Combinations Audited:** 12 (4 target states + 1 non-target state) × 3 transport modes = 15 combinations

**Files Created:** 5 audit outputs
1. `state_mode_dataset_matrix.csv` (72 rows)
2. `state_mode_processing_matrix.csv` (13 rows)
3. `state_mode_remaining_work.csv` (45 rows)
4. `state_mode_available_data_summary.md`
5. `state_coverage_audit_report.md` (this document)

**Repository Status:**
- No existing data modified ✅
- No existing reports modified ✅
- No files deleted ✅
- Only audit files created ✅

**Data Availability:**
- **AVAILABLE (substantial):** 3 state×mode combinations (Maharashtra Local Rail, Telangana Bus, Telangana Metro)
- **PARTIAL:** 2 combinations (Karnataka Metro, Tamil Nadu Metro)
- **BLOCKED:** 2 combinations (Delhi Bus, Delhi Metro)
- **MINIMAL:** 3 combinations (Maharashtra Bus, Karnataka Bus, Tamil Nadu Bus — fleet counts only)
- **MISSING:** 5 combinations (Maharashtra Metro, Tamil Nadu Local Rail, Telangana Local Rail, etc.)

**Major Remaining Datasets:** 45+ across data collection, cleaning, validation, EDA, geospatial, LGD, population, accessibility, gap analysis

**Exact Next Step:** Begin Tier 1 data collection (Delhi GTFS manual download, population data, Mumbai service frequency, Chennai Metro stations, LGD boundaries)

---

**Report Status:** ✅ COMPLETE  
**Audit Date:** 2026-09-29  
**Next Action:** Review audit findings with team; prioritize Tier 1 data collection
