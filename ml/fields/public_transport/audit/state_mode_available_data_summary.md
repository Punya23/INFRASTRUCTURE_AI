# STATE × TRANSPORT MODE — AVAILABLE DATA SUMMARY
**LokDrishti AI / INFRASTRUCTURE_AI Project**

**Date:** 2026-09-29  
**Audit Type:** Repository Inventory Audit (NO NEW DATA COLLECTED)  
**Target States:** Maharashtra, Delhi, Karnataka, Tamil Nadu  
**Transport Modes:** Bus, Metro, Local Rail

---

## Maharashtra

### Bus
**Available:**
- Smart Cities fleet counts for Pune (2,035 buses), Nagpur (387 buses) — NO stop coordinates, NO routes

**Partial:**
- Aggregate bus statistics (bus counts, terminal/stand/stop counts) for 3 cities
- No geographic data, no GTFS, no service schedules

**Missing:**
- MSRTC (Maharashtra State RTC) GTFS
- BEST (Mumbai) bus network data (stops, routes, GTFS)
- PMPML (Pune) bus network data (stops, routes, GTFS)
- Nagpur bus operator data
- Ridership for any Maharashtra bus system
- Service frequency for any Maharashtra bus system

**Blocked:**
- None identified

**Completed Processing:**
- Smart Cities fleet data: cleaning ✓, basic EDA ✓

**Remaining:**
- Collect GTFS from MSRTC, BEST, PMPML
- Geospatial analysis (blocked by missing stop coordinates)
- LGD mapping (blocked by missing data)
- Population analysis (blocked by missing data)
- Gap analysis (blocked by missing data)

---

### Metro
**Available:**
- None

**Partial:**
- Pune Metro: PDF DPR document only (not machine-readable)

**Missing:**
- Mumbai Metro (MMRDA/MML) stations, routes, GTFS
- Pune Metro stations, routes, GTFS (only PDF DPR available)
- Nagpur Metro (MahaMetro) stations, routes, GTFS
- Ridership for any Maharashtra metro system
- Service frequency for any Maharashtra metro system

**Blocked:**
- None identified

**Completed Processing:**
- None

**Remaining:**
- Collect Mumbai/Pune/Nagpur Metro station coordinates
- Collect GTFS for all three metro systems
- All geospatial, LGD, population, accessibility, gap analysis

---

### Local Rail
**Available:**
- **Mumbai Suburban Railway:** 106 stations with coordinates ✓
- Network geometry (line KML) ✓
- Station spacing analysis ✓
- Station catchments (500m/1km/2km) ✓
- Infrastructure gap analysis ✓ (11 potential spacing gaps identified)

**Partial:**
- Line names exist but no station-to-line mapping

**Missing:**
- Service frequency (trains/hour per station)
- Ridership (station-level boardings/alightings)
- Timetable (first/last trains, operating hours)
- Population data for catchment analysis
- Pune suburban rail (Pune-Lonavala EMU) stations and data

**Blocked:**
- Population analysis (no census ward-level data with boundaries)
- Service quality assessment (no frequency data)
- Demand analysis (no ridership data)

**Completed Processing:**
- M1 (Data Collection): ✓ COMPLETE
- M2 (EDA + Network Analysis): ✓ COMPLETE
- M3 (Geography + Accessibility): ✓ COMPLETE (theoretical catchments only)
- M4 (Gap Analysis): ✓ COMPLETE (11 potential spacing gaps; population/service impact UNKNOWN)
- Cleaning: ✓ COMPLETE
- Validation: ✓ COMPLETE
- Geospatial: ✓ COMPLETE (coordinates, spacing, catchments)

**Remaining:**
- Unblock population analysis: collect Census 2021 ward-level data + boundaries
- Unblock service analysis: collect MRVC service frequency
- Unblock demand analysis: collect MRVC ridership
- Collect Pune suburban rail data

---

## Delhi

### Bus
**Available:**
- None

**Partial:**
- None

**Missing:**
- Delhi DTC bus stops, routes, GTFS, ridership, frequency

**Blocked:**
- Delhi DTC GTFS: available on Delhi OTD portal but CSRF-protected download
- Manual download required (cannot automate via GET request)

**Completed Processing:**
- None

**Remaining:**
- Manual download Delhi DTC GTFS from https://otd.delhi.gov.in/data/staticDTC/
- Clean and validate GTFS
- All geospatial, LGD, population, accessibility, gap analysis

---

### Metro
**Available:**
- None

**Partial:**
- None

**Missing:**
- Delhi Metro (DMRC) stations, routes, GTFS, ridership, frequency

**Blocked:**
- Delhi Metro GTFS: available on Delhi OTD portal but CSRF-protected download
- Estimated ~262 stations, ~36 routes available in GTFS
- Manual download required (cannot automate via GET request)

**Completed Processing:**
- None

**Remaining:**
- Manual download Delhi Metro GTFS from https://otd.delhi.gov.in/data/staticDMRC/
- Clean and validate GTFS
- All geospatial, LGD, population, accessibility, gap analysis

---

### Local Rail
**Available:**
- Not applicable (Delhi does not have a suburban rail system like Mumbai/Chennai)

**Partial:**
- Not applicable

**Missing:**
- Not applicable

**Blocked:**
- Not applicable

**Completed Processing:**
- Not applicable

**Remaining:**
- None (no suburban rail system in Delhi)

---

## Karnataka

### Bus
**Available:**
- Smart Cities fleet counts for Bengaluru (6,677 buses total) — NO stop coordinates, NO routes

**Partial:**
- Aggregate bus statistics (bus counts, terminal/stand/stop counts) for Bengaluru only
- No geographic data, no GTFS, no service schedules

**Missing:**
- BMTC (Bengaluru) bus network data (stops, routes, GTFS)
- KSRTC (Karnataka State RTC) GTFS
- Ridership for any Karnataka bus system
- Service frequency for any Karnataka bus system

**Blocked:**
- None identified

**Completed Processing:**
- Smart Cities fleet data: cleaning ✓, basic EDA ✓

**Remaining:**
- Collect BMTC GTFS with stop coordinates and routes
- Collect KSRTC GTFS
- All geospatial, LGD, population, accessibility, gap analysis

---

### Metro
**Available:**
- **Bengaluru Metro:** 63 stations with coordinates ✓
- Network line geometry in KML ✓

**Partial:**
- Station codes/names file labeled "ridership" but contains NO actual ridership values

**Missing:**
- BMRCL GTFS (routes, trips, stop_times, frequencies)
- Service schedule data
- Actual ridership data
- Fare data

**Blocked:**
- None identified

**Completed Processing:**
- Station coordinates: cleaning ✓, validation ✓
- Basic EDA ✓ (63 stations identified)

**Remaining:**
- Collect BMRCL GTFS for service data
- Collect actual ridership data
- Geospatial analysis (catchments, spacing)
- LGD mapping
- Population analysis
- Gap analysis

---

### Local Rail
**Available:**
- Not applicable (Bengaluru does not currently have a suburban rail system)

**Partial:**
- Not applicable

**Missing:**
- Not applicable (future suburban rail projects may exist but no operational system)

**Blocked:**
- Not applicable

**Completed Processing:**
- Not applicable

**Remaining:**
- Investigate if Bengaluru suburban rail is operational or planned

---

## Tamil Nadu

### Bus
**Available:**
- Smart Cities fleet counts for Chennai (3,740 buses) — NO stop coordinates, NO routes

**Partial:**
- Aggregate bus statistics (bus counts, terminal/stand/stop counts) for Chennai only
- No geographic data, no GTFS, no service schedules

**Missing:**
- MTC (Chennai Metropolitan Transport) bus network data (stops, routes, GTFS)
- Ridership for any Tamil Nadu bus system
- Service frequency for any Tamil Nadu bus system

**Blocked:**
- None identified

**Completed Processing:**
- Smart Cities fleet data: cleaning ✓, basic EDA ✓

**Remaining:**
- Collect MTC GTFS with stop coordinates and routes
- All geospatial, LGD, population, accessibility, gap analysis

---

### Metro
**Available:**
- **Chennai Metro Ridership:** 39 months (Apr 2023 – Jun 2026) ✓
  - System-wide monthly ridership by ticket type (Closed Loop, QR, NCMC)
  - Total ridership: 345.3 million passengers over 39 months
  - Average monthly: 8.9 million passengers

**Partial:**
- None

**Missing:**
- Chennai Metro (CMRL) station coordinates
- Chennai Metro routes/lines
- CMRL GTFS (trips, stop_times, frequencies)
- Station-level ridership (only system-wide monthly totals available)
- Fare data

**Blocked:**
- None identified

**Completed Processing:**
- Ridership data: cleaning ✓, validation ✓, EDA ✓

**Remaining:**
- Collect CMRL station coordinates (KML/CSV)
- Collect CMRL GTFS
- Geospatial analysis (catchments, spacing) — blocked by missing station coordinates
- LGD mapping — blocked by missing station coordinates
- Population analysis — blocked by missing station coordinates
- Gap analysis — blocked by missing station coordinates

---

### Local Rail
**Available:**
- None

**Partial:**
- None

**Missing:**
- Chennai Suburban Rail stations with coordinates
- Chennai Suburban Rail routes
- Timetable (machine-readable format)
- Service frequency
- Ridership

**Blocked:**
- Official timetable exists on Southern Railway website (https://sr.indianrailways.gov.in/) but in PDF/HTML format only
- No machine-readable GTFS or station coordinate file found
- Manual extraction required

**Completed Processing:**
- None

**Remaining:**
- Extract Chennai Suburban Rail stations from timetable OR find alternate source
- Manual timetable extraction to GTFS format OR find alternate machine-readable source
- All geospatial, LGD, population, accessibility, gap analysis

---

## Other States Found in Repository

### Telangana (NOT a target state, but DATA AVAILABLE in repository)

#### Bus
**Available:**
- **TGSRTC Full GTFS:** ✓ COMPLETE
  - Agency: 1 record (Telangana State Road Transport Corporation)
  - Stops: 5,028 with coordinates ✓
  - Routes: 1,031 ✓
  - Trips: Full GTFS with trips, stop_times, calendar, feed_info
  - GeoJSON: Bus stops and route geometry created ✓

**Partial:**
- LGD mapping: some mapping done but incomplete

**Missing:**
- Ridership data

**Blocked:**
- None

**Completed Processing:**
- Data collection: ✓ COMPLETE
- Cleaning: ✓ COMPLETE
- Validation: ✓ COMPLETE
- EDA: ✓ COMPLETE
- Geospatial: ✓ COMPLETE (stop coordinates, route geometry)
- LGD mapping: ✓ PARTIAL

**Remaining:**
- Complete LGD mapping for all 5,028 stops (requires LGD spatial boundaries)
- Population analysis (requires census data)
- Catchment analysis (generate 500m/1km/2km buffers)
- Gap analysis (station spacing, coverage gaps)
- Ridership data collection

---

#### Metro
**Available:**
- **Hyderabad Metro (HMRL) Full GTFS:** ✓ COMPLETE
  - Stations: 57 with coordinates ✓
  - Platforms: 117 total
  - Routes: 3 corridors (Red/Blue/Green) ✓
  - Trips: 2,820 ✓
  - Stop times: 61,236 records ✓
  - Shapes: 6 shape linestrings (2,450 points) ✓
  - Calendar: 3 service patterns ✓
  - Fare attributes: 10 fare zones ✓
  - Fare rules: 3,249 origin-destination fare pairs ✓

**Partial:**
- None

**Missing:**
- Ridership data

**Blocked:**
- None

**Completed Processing:**
- Data collection: ✓ COMPLETE
- Cleaning: ✓ COMPLETE
- Validation: ✓ COMPLETE
- EDA: ✓ COMPLETE

**Remaining:**
- Geospatial analysis (catchments, spacing)
- LGD mapping
- Population analysis
- Accessibility analysis
- Gap analysis
- Ridership data collection

---

#### Local Rail
**Available:**
- None

**Partial:**
- None

**Missing:**
- Hyderabad MMTS (Multi-Modal Transport System) stations
- MMTS routes
- MMTS timetable
- Service frequency
- Ridership

**Blocked:**
- No machine-readable MMTS data found on South Central Railway website
- Third-party timetable aggregator exists (mmtstrains.in) but not authoritative

**Completed Processing:**
- None

**Remaining:**
- Collect MMTS station coordinates
- Extract or collect MMTS timetable
- All geospatial, LGD, population, accessibility, gap analysis

---

## Summary Statistics

### Data Availability by State × Mode

| State | Bus | Metro | Local Rail |
|-------|-----|-------|------------|
| **Maharashtra** | MINIMAL (fleet counts only) | MISSING | **SUBSTANTIAL** (Mumbai M1-M4 complete) |
| **Delhi** | BLOCKED (GTFS exists) | BLOCKED (GTFS exists) | NOT_APPLICABLE |
| **Karnataka** | MINIMAL (fleet counts only) | PARTIAL (stations only) | NOT_APPLICABLE |
| **Tamil Nadu** | MINIMAL (fleet counts only) | PARTIAL (ridership only) | BLOCKED (timetable PDF only) |
| **Telangana** (other) | **SUBSTANTIAL** (full GTFS) | **SUBSTANTIAL** (full GTFS) | MISSING |

### Processing Completion Status

**COMPLETE (all stages done):**
- Maharashtra Local Rail (Mumbai Suburban): M1-M4 ✓
- Telangana Bus (TGSRTC): Data + cleaning + validation + EDA + geospatial ✓
- Telangana Metro (Hyderabad): Data + cleaning + validation + EDA ✓

**PARTIAL (some stages done):**
- Karnataka Metro (Bengaluru): Station data + cleaning + EDA ✓; GTFS missing
- Tamil Nadu Metro (Chennai): Ridership data + cleaning + EDA ✓; station/network missing
- All Smart Cities bus fleet: Cleaning + EDA ✓; geographic data missing

**BLOCKED (source identified but access blocked):**
- Delhi Bus: GTFS exists but manual download required
- Delhi Metro: GTFS exists but manual download required
- Tamil Nadu Local Rail: Timetable exists but PDF only

**MISSING (no data collected):**
- Maharashtra Bus (MSRTC, BEST, PMPML): No GTFS
- Maharashtra Metro (Mumbai, Pune, Nagpur): No data
- Karnataka Bus (BMTC): No GTFS
- Tamil Nadu Bus (MTC): No GTFS
- Tamil Nadu Metro (CMRL): No station/network data
- Telangana Local Rail (MMTS): No data

### Record Counts (Repository Totals)

**Bus:**
- Stops: 5,028 (Telangana only)
- Routes: 1,031 (Telangana only)
- Fleet records: 74 cities (Smart Cities; counts only, no coordinates)

**Metro:**
- Stations: 120 total (57 Hyderabad, 63 Bengaluru)
- Routes: 6 (3 Hyderabad, 3 implicit Bengaluru lines)
- Ridership: 39 monthly records (Chennai system-wide)

**Local Rail:**
- Stations: 106 (Mumbai Suburban only)
- Network length: 307.46 km (Mumbai only)
- Potential spacing gaps: 11 (Mumbai M4 analysis)

---

## Data Quality Assessment

### HIGH QUALITY (verified coordinates, complete GTFS, full pipeline):
- Maharashtra Local Rail (Mumbai Suburban): 106 stations, M1-M4 complete
- Telangana Bus (TGSRTC): 5,028 stops, full GTFS, cleaning + validation + EDA + geospatial ✓
- Telangana Metro (Hyderabad): 57 stations, full GTFS with shapes + fares, cleaning + validation + EDA ✓

### MEDIUM QUALITY (coordinates available, partial data):
- Karnataka Metro (Bengaluru): 63 stations with coordinates, no GTFS
- Tamil Nadu Metro (Chennai): Ridership data complete, no station/network data

### LOW QUALITY (aggregate counts only, no coordinates):
- All Smart Cities bus fleet data: 74 cities, fleet/terminal/stop counts only, NO stop coordinates

### BLOCKED (source exists but not accessible):
- Delhi Bus (DTC): Full GTFS available but CSRF-protected
- Delhi Metro (DMRC): Full GTFS available but CSRF-protected
- Tamil Nadu Local Rail (Chennai): Timetable in PDF/HTML only

### MISSING (no source identified or no data collected):
- All Maharashtra bus operators (MSRTC, BEST, PMPML)
- All Maharashtra metro systems (Mumbai, Pune, Nagpur)
- Karnataka bus (BMTC)
- Tamil Nadu bus (MTC)
- Telangana local rail (MMTS)

---

## Critical Gaps

### Geographic Coverage Gaps:
- **Zero bus network data** for Maharashtra, Karnataka, Tamil Nadu target states (only Telangana has GTFS)
- **Zero metro network data** for Maharashtra target state
- **Zero local rail data** for Delhi, Karnataka, Tamil Nadu target states (only Maharashtra Mumbai has data)

### Data Type Gaps (across all states):
- **Population:** No census ward-level population data with spatial boundaries for ANY state
- **Service Frequency:** Available only in Telangana/Hyderabad GTFS; missing for all other systems
- **Ridership:** Only Chennai Metro has ridership (system-wide monthly); NO station-level ridership anywhere
- **LGD Boundaries:** LGD codes available but NO spatial polygon geometries for ANY geography

### Processing Gaps:
- **Geospatial analysis:** Only Mumbai Local Rail and Telangana Bus complete; all other systems need catchments, spacing, network analysis
- **Gap analysis:** Only Mumbai Local Rail complete (M4); all other systems need gap identification
- **Population analysis:** BLOCKED for all systems (no population data)
- **LGD integration:** BLOCKED for all systems (no LGD spatial boundaries)

---

## Next Steps

See `state_mode_remaining_work.csv` for detailed priority list.

**Immediate priorities:**
1. Manual download Delhi Bus + Metro GTFS (unblocks 2 state×mode combinations)
2. Collect Mumbai/Bengaluru/Chennai bus GTFS (unblocks 3 major cities)
3. Collect Chennai Metro station coordinates (unblocks network analysis)
4. Collect population data (unblocks population analysis for all systems)
5. Collect LGD spatial boundaries (unblocks LGD integration for all systems)
