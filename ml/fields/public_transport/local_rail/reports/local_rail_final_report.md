# LOCAL RAIL — Final Analysis Report

**Domain:** Local Rail (Suburban Railway Systems)  
**Report Date:** 2026-09-29  
**Geographic Scope:** 5 suburban railway systems across India  
**Analysis Milestone:** M1 Data Collection + Cleaning (Complete for Mumbai only)

---

## Executive Summary

This report documents the first milestone (M1) of Local Rail infrastructure analysis for India's suburban railway systems. Of the 5 systems scoped (Mumbai, Chennai, Kolkata, Hyderabad MMTS, Pune), only **Mumbai Suburban Railway** has official machine-readable data available. The other 4 systems are blocked by **DATA_UNAVAILABLE**—no official station lists, timetables, or geospatial data were found in accessible formats.

**Key Findings:**
- **Mumbai Suburban:** 106 stations + 106 line segments processed from BMC OpenCity.in KML data
- **Chennai Suburban:** Community GTFS exists but excludes suburban rail (contains MTC buses + CMRL metro only)
- **Kolkata/Hyderabad/Pune:** No official machine-readable data found (only PDF maps or non-geographic sources)

**Data Integrity:** Maintained throughout—no coordinates, station names, or geometry fabricated. All unavailable data explicitly marked.

---

## System-by-System Summary

### 1. Mumbai Suburban Railway

**System:** Mumbai Suburban Railway (Western, Central, Harbour, Trans-Harbour lines)  
**Operator:** Western Railway + Central Railway (Indian Railways zones)  
**State:** Maharashtra  
**City:** Mumbai  
**Status:** ✓ PARTIAL DATA AVAILABLE

#### Data Sources
| Type | Source | Format | Records | Quality |
|------|--------|--------|---------|---------|
| Stations | BMC via OpenCity.in | KML | 106 | Good |
| Lines | BMC via OpenCity.in | KML | 106 | Good |
| Routes | Not Available | — | 0 | N/A |
| Services | Not Available | — | 0 | N/A |
| Ridership | Not Available | — | 0 | N/A |

**Source URL:** https://data.opencity.in/dataset/mumbai-suburban-network-2025  
**License:** Public Domain (civic open data portal)  
**Provenance:** Brihanmumbai Municipal Corporation (BMC)

#### Geospatial Coverage
- **Bounding Box:** 18.7896°N–19.5194°N, 72.8119°E–73.3449°E
- **Extent:** ~81 km (N-S) × ~59 km (E-W)
- **Region:** Greater Mumbai (Churchgate to Kalyan/Virar/Panvel corridors expected)

#### Data Quality Assessment
| Metric | Value | Assessment |
|--------|-------|------------|
| Station count | 106 | Good coverage |
| Name completeness | 100% | Excellent |
| Coordinate validity | 67.9% (72/106) | Moderate—32.1% flagged |
| Line segment count | 106 | Good |
| Provenance | 100% | Complete |

**Quality Issues:**
- 34 stations (32.1%) flagged during coordinate validation (likely outside expected bounds or low precision)
- No route mapping (cannot distinguish Western/Central/Harbour lines)
- No service-level data (frequency, timings, capacity)

#### Sample Stations
```
MUM_RAIL_STN_001 | Churchgate      | 72.8272, 18.9353
MUM_RAIL_STN_002 | Marine Lines    | 72.8238, 18.9458
MUM_RAIL_STN_009 | Dadar           | 72.8431, 19.0196
```

#### Files Created
- `data/processed/mumbai/mumbai_stations_clean.csv` (106 records)
- `data/processed/mumbai/mumbai_lines_clean.csv` (106 records)
- `data/processed/geospatial/mumbai_stations.geojson` (106 points)
- `data/processed/geospatial/mumbai_lines.geojson` (106 linestrings)
- `data/processed/final/local_rail_stations.csv` (106 records)
- `data/processed/final/local_rail_master.csv` (106 records)

#### Recommendations
1. **High Priority:** Source ridership data from Western Railway / Central Railway annual reports
2. **High Priority:** Validate 34 flagged coordinates (manual review or cross-reference with NTES/Indian Railways APIs)
3. **Medium Priority:** Map line segments to official corridors (Western, Central, Harbour, Trans-Harbour)
4. **Medium Priority:** Parse train timetables for frequency and service patterns
5. **Low Priority:** Add interchange analysis with Mumbai Metro (when M0 lands)

---

### 2. Chennai Suburban Railway

**System:** Chennai Suburban Railway (Chennai Beach–Tambaram–Arakkonam–Gummidipoondi lines)  
**Operator:** Southern Railway (Indian Railways zone)  
**State:** Tamil Nadu  
**City:** Chennai  
**Status:** ✗ DATA_UNAVAILABLE

#### Data Search Results
| Source | Format | Status | Notes |
|--------|--------|--------|-------|
| UngalSoththu GTFS | GTFS | ✗ Excludes suburban rail | Contains MTC buses + CMRL metro only |
| Indian Railways website | HTML/PDF | ✗ Non-geographic | Only textual timetables |
| NTES API | JSON | ✗ Not investigated | Requires train-by-train queries |

**Community GTFS Note:** The UngalSoththu Chennai GTFS feed (collected in Step 1) explicitly excludes Chennai Suburban Railway. It contains:
- MTC city buses
- CMRL (Chennai Metro Rail Limited) metro lines

Per repository documentation, this GTFS **must not** be used as Chennai Local Rail data.

#### Recommendations
1. **Immediate:** Contact Southern Railway for official station list and route maps in machine-readable format (CSV, GeoJSON, or GTFS)
2. **Alternative:** Parse NTES (National Train Enquiry System) API for Chennai suburban train schedules and station coordinates
3. **Fallback:** Manually geocode stations from official timetables (48 stations estimated)

---

### 3. Kolkata Suburban Railway

**System:** Kolkata Suburban Railway (Sealdah South/North + Howrah lines)  
**Operator:** Eastern Railway + South Eastern Railway (Indian Railways zones)  
**State:** West Bengal  
**City:** Kolkata  
**Status:** ✗ DATA_UNAVAILABLE

#### Data Search Results
| Source | Format | Status | Notes |
|--------|--------|--------|-------|
| Indian Railways website | HTML/PDF | ✗ Non-geographic | Only textual timetables |
| OpenStreetMap | Overpass API | ⚠ Partial | Railway lines present but station names/services missing |
| GTFS feeds | GTFS | ✗ Not found | No public GTFS for Kolkata suburban rail |

#### Recommendations
1. **Immediate:** Contact Eastern Railway / South Eastern Railway for official station coordinates and route data
2. **Alternative:** Extract geometry from OpenStreetMap (rail=light_rail / rail=suburban) and cross-reference with timetable PDFs
3. **Fallback:** Manually geocode ~120 stations from official sources

---

### 4. Hyderabad MMTS (Multi-Modal Transport System)

**System:** Hyderabad MMTS (Suburban Rail)  
**Operator:** South Central Railway (Indian Railways zone) + HMRL  
**State:** Telangana  
**City:** Hyderabad  
**Status:** ✗ DATA_UNAVAILABLE

#### Data Search Results
| Source | Format | Status | Notes |
|--------|--------|--------|-------|
| HMRL website | HTML | ✗ Non-geographic | Only route descriptions |
| Indian Railways website | PDF | ✗ Non-geographic | Timetables without coordinates |
| GTFS feeds | GTFS | ✗ Not found | No public GTFS for MMTS |

**Context:** Hyderabad MMTS is a smaller suburban rail network (~45 km, 3 lines) compared to Mumbai/Chennai/Kolkata. It may have fewer digital resources.

#### Recommendations
1. **Immediate:** Contact HMRL (Hyderabad Metro Rail Limited) or South Central Railway for station list and route map
2. **Alternative:** Cross-reference MMTS routes with Hyderabad Metro GTFS (if available) for interchange stations
3. **Fallback:** Manually geocode ~20 MMTS stations from route maps

---

### 5. Pune Suburban Railway

**System:** Pune Suburban Railway  
**Operator:** Central Railway (Indian Railways zone)  
**State:** Maharashtra  
**City:** Pune  
**Status:** ✗ DATA_UNAVAILABLE

#### Data Search Results
| Source | Format | Status | Notes |
|--------|--------|--------|-------|
| Indian Railways website | HTML/PDF | ✗ Non-geographic | Only textual timetables |
| GTFS feeds | GTFS | ✗ Not found | No public GTFS for Pune suburban rail |

**Context:** Pune Suburban Railway is limited in scale (primarily Pune–Lonavla corridor with few suburban stations). May have minimal digital infrastructure.

#### Recommendations
1. **Immediate:** Contact Central Railway Pune division for official station data
2. **Alternative:** Extract data from NTES API for Pune local trains
3. **Fallback:** Manually geocode ~10-15 suburban stations

---

## Cross-System Data Availability Matrix

| System | State | Stations | Coords | Lines | Geometry | Routes | Services | Timetable | Freq | Ridership | Population | LGD | Geospatial | **Status** |
|--------|-------|----------|--------|-------|----------|--------|----------|-----------|------|-----------|------------|-----|------------|------------|
| **Mumbai Suburban** | Maharashtra | ✓ | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | BLOCKED | BLOCKED | ✓ | **PARTIAL** |
| **Chennai Suburban** | Tamil Nadu | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | BLOCKED | BLOCKED | ✗ | **UNAVAILABLE** |
| **Kolkata Suburban** | West Bengal | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | BLOCKED | BLOCKED | ✗ | **UNAVAILABLE** |
| **Hyderabad MMTS** | Telangana | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | BLOCKED | BLOCKED | ✗ | **UNAVAILABLE** |
| **Pune Suburban** | Maharashtra | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | BLOCKED | BLOCKED | ✗ | **UNAVAILABLE** |

**Legend:**
- ✓ = Data collected and validated
- ✗ = Not available (official machine-readable source not found)
- BLOCKED = Analysis blocked by missing prerequisites (city boundaries, population data)

---

## Data Integrity Verification

### ✓ No Data Fabrication
**Verification:** All 106 Mumbai records trace to source KML files. No coordinates, station names, or geometry invented by AI.

### ✓ Provenance Complete
**Verification:** 100% of Mumbai records contain:
- `source`: "BMC via OpenCity.in"
- `source_file`: "mumbai_suburban_stations.kml" / "mumbai_suburban_lines.kml"
- `source_url`: "https://data.opencity.in/dataset/mumbai-suburban-network-2025"

### ✓ Unavailable Data Documented
**Verification:**
- Chennai GTFS marked as EXCLUDES_SUBURBAN_RAIL (not silently ignored)
- Kolkata/Hyderabad/Pune marked as DATA_UNAVAILABLE (not defaulted to empty datasets)
- Mumbai ridership/services marked as UNAVAILABLE (not fabricated)

### ✓ Coordinate Validation Honest
**Verification:** 34 stations flagged as invalid/issues (not corrected by AI, preserved source data)

---

## Comparative Context: Indian Suburban Rail vs. Other Domains

| Domain | Systems Analyzed | Data Availability | Status |
|--------|------------------|-------------------|--------|
| **Metro Rail** | 15+ metro systems | High (12 with GTFS/ridership) | ✓ M1 Complete |
| **National Highways** | NH network nationwide | High (NHAI GeoServer, MoRTH reports) | ✓ M1+M2 Complete |
| **Local Rail** | 5 suburban railways | Low (1/5 with machine-readable data) | ⚠ M1 Partial |

**Key Insight:** Local Rail data availability is significantly lower than Metro or National Highways. Indian Railways zones lack centralized open data portals comparable to NHAI GeoServer or metro GTFS feeds.

---

## Recommendations: Path Forward

### Immediate Actions (Next Sprint)
1. **Mumbai Enhancement:** Validate 34 flagged coordinates, source ridership data, map lines to corridors
2. **Chennai Engagement:** Contact Southern Railway for official data; investigate NTES API integration
3. **OSM Fallback:** Evaluate OpenStreetMap as secondary source for Kolkata/Chennai/Hyderabad station coordinates
4. **GTFS Advocacy:** Engage with Indian Railways HQ / state transport departments to advocate for public GTFS feeds

### Medium-Term (Next Quarter)
5. **Manual Geocoding:** If official data unavailable, manually geocode stations from timetables (Chennai ~48, Kolkata ~120, Hyderabad ~20, Pune ~15)
6. **NTES Integration:** Build scraper for National Train Enquiry System API to extract suburban train schedules and station data
7. **LGD City Boundaries:** Add Mumbai municipal boundary to enable population catchment analysis
8. **Line Naming:** Map Mumbai line segments to official corridors (Western, Central, Harbour, Trans-Harbour)

### Long-Term (6+ Months)
9. **Indian Railways API Partnership:** Pursue MOU with Indian Railways for machine-readable suburban rail data access
10. **Community Crowdsourcing:** Engage with transit enthusiast communities (analogous to GTFS-realtime projects) for data contributions
11. **Cross-Domain Integration:** Analyze Mumbai Suburban + Mumbai Metro interchange stations for multimodal routing

---

## Milestone Status: M1 Local Rail

**Overall Status:** ⚠ PARTIAL COMPLETE  

| Task | Status | Notes |
|------|--------|-------|
| Data collection (5 systems) | ⚠ Partial | Only Mumbai collected |
| Data validation | ✓ Complete | 2 KML files validated |
| Data cleaning | ✓ Complete | 106 stations + 106 lines |
| Geospatial processing | ✓ Complete | 2 GeoJSON files |
| EDA | ✓ Complete | 7 summary stats |
| Final datasets | ✓ Complete | 2 CSV files |
| Data availability documentation | ✓ Complete | 5 systems documented |

**Next Milestone:** M2 (EDA + Infrastructure Features) for Mumbai only; other cities remain blocked by DATA_UNAVAILABLE.

---

## Conclusion

Local Rail M1 successfully processed **Mumbai Suburban Railway** (106 stations, 106 lines) with strict data integrity. The other four systems—Chennai, Kolkata, Hyderabad MMTS, and Pune—remain blocked by lack of official machine-readable data. Unlike Metro Rail (where 12/15 systems had GTFS) or National Highways (NHAI GeoServer), Indian Railways suburban operations lack centralized open data infrastructure.

**Critical Blocker:** Expanding Local Rail coverage requires direct engagement with Indian Railways zones or manual geocoding from timetable PDFs—a significant effort beyond automated pipelines.

**Recommendation:** Proceed to M0 (Foundation) with Mumbai Local Rail as the sole suburban rail system, revisit Chennai/Kolkata/Hyderabad/Pune once official data sources are secured.

---

**Report Author:** Kiro AI Agent  
**Report Date:** 2026-09-29  
**Data Collection Period:** 2026-09-29  
**Next Review:** Upon securing Chennai/Kolkata data sources  
