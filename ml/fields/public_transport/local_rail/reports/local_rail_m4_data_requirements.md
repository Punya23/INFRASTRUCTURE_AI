# LOCAL RAIL M4 — DATA REQUIREMENTS TO UNBLOCK ANALYSIS
**Mumbai Suburban Railway System**

**Date:** 2026-09-29  
**Purpose:** Document data needs to unblock 12 blocked indicators  
**Context:** M4 gap analysis completed with geographic spacing only; population/service analysis BLOCKED

---

## Overview

M4 identified **12 blocked indicators** due to missing data. This document specifies exactly what data is needed, in what format, from which sources, and what analyses each dataset would enable.

**Current State:** 4/11 data components available (36.4%)  
**Target State:** 11/11 components → enable full infrastructure gap analysis

---

## 1. CRITICAL PRIORITY — Population Data

### 1.1 Required Data

**Dataset:** Census 2021 population data for Mumbai (ward/ULB level)

**Required Fields:**
- Geographic unit identifier (ward code, ULB code, or LGD code)
- Total population (2021)
- Population density (persons/km²)
- Geographic boundaries (polygon geometry in WGS84/EPSG:4326)

**Preferred Format:** GeoJSON, Shapefile, or PostGIS-compatible format with population attributes

**Minimum Spatial Resolution:** Ward level (Mumbai has ~227 wards)

**Potential Sources:**
1. **Census of India 2021** (official)
   - URL: https://censusindia.gov.in/
   - Status: Check availability of digital spatial data
   - License: Government Open Data (typically CC BY 4.0 or similar)

2. **DataMeet India Spatial Data** (community-curated)
   - URL: https://github.com/datameet/maps
   - Status: Check for Mumbai ward boundaries + population attributes
   - License: CC BY 4.0 (typical for DataMeet)

3. **Survey of India (SOI) boundaries**
   - URL: https://www.surveyofindia.gov.in/
   - Status: Official boundaries; check digital availability
   - License: Verify terms

4. **State Government Open Data Portal**
   - URL: https://data.gov.in/ (search: Mumbai wards, Maharashtra boundaries)
   - Status: Variable quality; verify spatial accuracy
   - License: Verify per dataset

### 1.2 Quality Requirements

**Mandatory:**
- ✅ Polygon geometries (not just centroids)
- ✅ Population totals per spatial unit
- ✅ Valid geometries (no self-intersections, gaps, or overlaps)
- ✅ CRS: WGS84 (EPSG:4326) or convertible

**Optional (nice to have):**
- Population breakdown (age, gender, employment)
- Socioeconomic indicators (literacy, income)
- Housing density

### 1.3 Validation Steps Before Use

1. **Spatial integrity check:**
   - Load in QGIS/PostGIS
   - Check for gaps, overlaps, invalid geometries
   - Verify extent covers all 106 stations

2. **Attribute completeness:**
   - No NULL population values
   - Population totals sum to known Mumbai metro population (~12-20M)
   - Density values reasonable (not negative, not absurd)

3. **License verification:**
   - Confirm open license or government open data
   - Document attribution requirements
   - Check share-alike obligations

4. **Provenance documentation:**
   - Source URL
   - Download date
   - Version/release date
   - Contact for updates

### 1.4 Indicators Unblocked by This Data

✅ `population_per_station` → Calculate average population served per station  
✅ `stations_per_100k_population` → Normalize station count by population  
✅ `population_within_500m` → Identify high-demand vs low-demand areas  
✅ `population_within_1km` → Prioritize gap interventions by population need  
✅ `population_within_2km` → Extended catchment analysis  
✅ `average_population_per_catchment` → Service equity assessment  

**Impact:** Transforms "geographic spacing outliers" → "confirmed underserved populations"

---

## 2. CRITICAL PRIORITY — Service Frequency Data

### 2.1 Required Data

**Dataset:** Train service frequency for Mumbai Suburban Railway

**Required Fields:**
- Station ID or station name
- Trains per hour (peak hours: 7-10 AM, 5-8 PM)
- Trains per hour (off-peak hours)
- Operating hours (first train, last train)
- Line ID (Western, Central, Harbour, Trans-Harbour)

**Preferred Format:** CSV, JSON, or structured spreadsheet

**Minimum Granularity:** Station-level, peak vs off-peak

**Potential Sources:**
1. **Mumbai Railway Vikas Corporation (MRVC)**
   - URL: http://www.mrvc.indianrail.gov.in/
   - Status: Check for published service frequency data
   - License: Likely government data (verify terms)

2. **Indian Railways data portal**
   - URL: Check Ministry of Railways open data initiatives
   - Status: May have aggregated service data
   - License: Verify per dataset

3. **General Transit Feed Specification (GTFS)** (if available)
   - Format: GTFS standard (stop_times.txt, trips.txt, frequencies.txt)
   - Status: Check if MRVC or Indian Railways publish GTFS
   - License: Typically open (CC BY or public domain)

4. **Crowdsourced timetables** (last resort)
   - Sources: Transit apps, Wikipedia timetables
   - Status: Less reliable, requires verification
   - License: Variable; check attribution

### 2.2 Quality Requirements

**Mandatory:**
- ✅ Station-level granularity (not line-level averages)
- ✅ Peak vs off-peak distinction
- ✅ All 106 stations covered (or document exceptions)
- ✅ Recent data (2024-2025 preferred)

**Optional (nice to have):**
- Direction-specific frequency (inbound vs outbound)
- Weekend vs weekday service
- Express vs local service distinction

### 2.3 Validation Steps Before Use

1. **Coverage check:**
   - All 106 M1 stations matched to frequency data
   - Document stations with missing frequency (if any)

2. **Sanity checks:**
   - Peak frequency > off-peak frequency (expected pattern)
   - Frequency values reasonable (e.g., 2-30 trains/hour for Mumbai local)
   - No negative or zero values where service exists

3. **Cross-validation:**
   - Compare to published timetables (spot-check)
   - Compare to user-reported frequencies (if available)

4. **Provenance documentation:**
   - Source, download date, version, contact

### 2.4 Indicators Unblocked by This Data

✅ `average_service_frequency` → Identify poorly-served stations  
✅ `peak_vs_offpeak_ratio` → Service equity assessment  
✅ `service_hours_per_day` → Accessibility for shift workers, late travelers  

**Impact:** Enables "effective accessibility" analysis (spacing + service quality)

---

## 3. HIGH PRIORITY — Ridership Data

### 3.1 Required Data

**Dataset:** Station-level ridership (daily boardings/alightings)

**Required Fields:**
- Station ID or station name
- Average daily boardings (or entries)
- Average daily alightings (or exits)
- Year/period of measurement
- Measurement method (ticket sales, AFC data, manual count)

**Preferred Format:** CSV, JSON, or structured spreadsheet

**Minimum Granularity:** Station-level, annual average

**Potential Sources:**
1. **MRVC annual reports**
   - URL: http://www.mrvc.indianrail.gov.in/
   - Status: Check for published ridership statistics
   - License: Likely government data (verify terms)

2. **Indian Railways statistics**
   - URL: Ministry of Railways annual reports
   - Status: May have aggregated ridership
   - License: Government open data (verify)

3. **Research papers / city reports**
   - Sources: Academic studies, city planning documents
   - Status: Often cite ridership data from official sources
   - License: Cite original source

### 3.2 Quality Requirements

**Mandatory:**
- ✅ Station-level granularity
- ✅ Numerical values (not just "high/medium/low")
- ✅ Documented measurement period (e.g., 2024 annual average)
- ✅ Measurement method documented

**Optional (nice to have):**
- Peak hour ridership
- Directional split (inbound vs outbound)
- Weekend vs weekday

### 3.3 Validation Steps Before Use

1. **Coverage check:**
   - Match to 106 M1 stations
   - Document stations with missing ridership

2. **Sanity checks:**
   - Ridership values reasonable (e.g., 1,000-500,000 per station/day for Mumbai)
   - Total ridership sums to known network ridership (~7-8 million/day for Mumbai local)

3. **Outlier investigation:**
   - Very high ridership → major interchange or terminus (expected)
   - Very low ridership → edge station or data error (investigate)

4. **Provenance documentation:**
   - Source, measurement period, method, download date

### 3.4 Indicators Unblocked by This Data

✅ `average_ridership_per_station` → Identify high-demand vs underutilized stations  
✅ `ridership_per_km` → Network efficiency metric  

**Impact:** Prioritize gap interventions by actual demand (not just spacing)

---

## 4. MEDIUM PRIORITY — LGD Spatial Boundaries

### 4.1 Current Status

**What We Have:** LGD codes (Local Government Directory codes) for some stations

**What We Need:** Polygon geometries for LGD administrative units (ULBs, wards)

**Why It Matters:** Enable spatial join of population data to station catchments

### 4.2 Required Data

**Dataset:** LGD spatial boundaries (ward/ULB polygons)

**Required Fields:**
- LGD code (matches codes in M3 data)
- Polygon geometry (WGS84/EPSG:4326)
- Administrative level (ward, ULB, district)
- Name (for validation)

**Preferred Format:** GeoJSON, Shapefile, or PostGIS-compatible

**Potential Sources:**
1. **LGD official portal**
   - URL: https://lgdirectory.gov.in/
   - Status: Has LGD codes; check for downloadable spatial data
   - License: Verify government open data terms

2. **DataMeet India Spatial Data**
   - URL: https://github.com/datameet/maps
   - Status: May have LGD-linked boundaries
   - License: CC BY 4.0 (typical)

3. **Survey of India boundaries**
   - URL: https://www.surveyofindia.gov.in/
   - Status: Official source; check digital availability
   - License: Verify terms

### 4.3 Quality Requirements

**Mandatory:**
- ✅ LGD code attribute (for joining to M3 codes)
- ✅ Valid polygon geometries
- ✅ Coverage of Mumbai area
- ✅ CRS: WGS84 or convertible

### 4.4 Indicators Unblocked by This Data

✅ `spatial_overlap_lgd_boundaries` → Link stations to administrative units  
(Enables future analyses: governance, budget allocation, planning jurisdiction)

**Impact:** Medium — useful for administrative context but not critical for gap analysis

---

## 5. LOW PRIORITY — Fare and Operating Hours Data

### 5.1 Fare Data

**Purpose:** Affordability analysis (future enhancement)

**Required:** Station-to-station fare matrix or distance-based fare formula

**Sources:** Indian Railways fare policy, MRVC published fares

**Impact:** Enables affordability vs income analysis (requires income data too)

### 5.2 Operating Hours Data

**Purpose:** Service span analysis (partially covered by service frequency data)

**Required:** First train and last train times per station

**Sources:** Published timetables, GTFS (if available)

**Impact:** Identifies stations with limited service hours (accessibility for shift workers)

---

## 6. Data Acquisition Workflow

### 6.1 Recommended Sequence

1. **Population data** (highest impact)
2. **Service frequency data** (highest impact)
3. **Ridership data** (high impact)
4. **LGD spatial boundaries** (medium impact)
5. **Fare/operating hours** (low impact, future enhancement)

### 6.2 Data Acquisition Steps (per dataset)

**Step 1: Source identification**
- Check potential sources listed in this document
- Search data.gov.in, state portals, academic papers
- Contact data publishers if necessary

**Step 2: License verification**
- Confirm open license or government open data
- Document attribution requirements
- Check share-alike obligations (e.g., ODbL for OSM-derived data)

**Step 3: Download and initial inspection**
- Download to `data/raw/local_rail/`
- Quick inspection: file format, size, column names
- Check for README, metadata, data dictionary

**Step 4: Data validation**
- Run quality checks (Section 1.3, 2.3, 3.3, 4.3 above)
- Document issues: missing values, invalid geometries, outliers
- Decide: usable as-is, needs cleaning, or unusable

**Step 5: Manifest creation**
- Create YAML manifest in `data/manifests/`
- Document: source, URL, license, fetch_date, description, file_path
- Add to `config/sources.yaml`

**Step 6: Integration**
- Update M3 pipeline to incorporate population/boundaries
- Create M4A pipeline for service frequency integration
- Update M4 gap analysis to use new indicators

**Step 7: Documentation**
- Update `local_rail_m4_gap_analysis.md` with new findings
- Update blocked indicators table (remove unblocked indicators)
- Update data completeness matrix

---

## 7. Fallback Strategies (if primary sources unavailable)

### 7.1 Population Data Fallback

**Option A:** WorldPop raster data (1km resolution)
- URL: https://www.worldpop.org/
- Format: Raster (TIF), requires zonal statistics to summarize by catchment
- License: CC BY 4.0
- Limitation: Lower resolution than ward-level census

**Option B:** GHSL population grid (1km resolution)
- Already downloaded for M3 (ghsl_pop_2020_1km)
- Format: Raster (TIF)
- Limitation: 1km resolution, older data (2020)

**Option C:** Estimate from built-up area + density assumptions
- Use GHSL built-up raster + typical Mumbai density (20,000-30,000 per km²)
- Limitation: High uncertainty; document as ESTIMATED

**Recommendation:** Pursue Option A (WorldPop) if census data unavailable; Option B as last resort

### 7.2 Service Frequency Fallback

**Option A:** Crowdsourced timetable scraping
- Sources: Wikipedia timetables, transit apps
- Method: Manual extraction + validation
- Limitation: Requires verification; may be outdated

**Option B:** Proxy from line-level service
- Use Western/Central/Harbour line averages
- Apply to all stations on that line
- Limitation: Ignores station-level variation (e.g., express skips)

**Recommendation:** Pursue Option A with careful validation; document as CROWDSOURCED

### 7.3 Ridership Fallback

**Option A:** Estimate from service frequency + capacity
- Formula: ridership ≈ trains/hour × capacity/train × operating hours
- Typical Mumbai local: 12-15 coaches, ~300 passengers/coach (peak), ~4,500/train
- Limitation: High uncertainty; actual load factor varies

**Option B:** Use network-level ridership + station weighting
- Total Mumbai local ridership: ~7.5 million/day
- Weight by service frequency, population catchment, or network position
- Limitation: Distributional assumptions; high uncertainty

**Recommendation:** Pursue Option A if partial service frequency data available; document as ESTIMATED

---

## 8. Expected Outcomes After Data Integration

### 8.1 New Indicators (12 currently blocked → 11 unblocked)

**Population-based (6):**
- ✅ Population per station (thousands)
- ✅ Stations per 100k population
- ✅ Population within 500m catchment
- ✅ Population within 1km catchment
- ✅ Population within 2km catchment
- ✅ Average population per catchment

**Service-based (3):**
- ✅ Average service frequency (trains/hour)
- ✅ Peak vs off-peak service ratio
- ✅ Service hours per day

**Ridership-based (2):**
- ✅ Average ridership per station (daily boardings)
- ✅ Ridership per km of network

**Other (1):**
- ✅ Spatial overlap with LGD boundaries (if geometries acquired)

### 8.2 New Analyses Enabled

**A. Underserved Population Identification**
- Gaps with high population catchments → priority interventions
- Gaps with low population → lower priority (appropriate low-density service)

**B. Service Quality Assessment**
- Stations with large spacing + low frequency → confirmed accessibility gaps
- Stations with large spacing + high frequency → may be adequate

**C. Demand-Based Gap Prioritization**
- High ridership + large spacing → urgent intervention
- Low ridership + large spacing → monitor, lower priority

**D. Equity Analysis**
- Population per station vs service frequency
- Identify stations serving disproportionately large populations
- Identify areas with low service per capita

**E. Effective Accessibility Calculation**
- Catchment area × service frequency → "effective" accessibility
- Replace theoretical catchments with service-weighted catchments

### 8.3 Updated Gap Classification

**Current Status:** All 11 gaps labeled `POTENTIAL_GEOGRAPHIC_GAP`

**After Data Integration:**
- `CONFIRMED_UNDERSERVED_POPULATION` (high population, low service)
- `CONFIRMED_SERVICE_GAP` (adequate population, inadequate frequency)
- `LOW_PRIORITY_GAP` (low population, low demand, appropriate low service)
- `DATA_INCOMPLETE` (partial data only)

**Impact:** Move from "potential" → "confirmed" gaps with prioritization

---

## 9. Summary

**Current State:** 4/11 data components available; 12 indicators BLOCKED

**Critical Data Needs:**
1. Population data (census ward-level + boundaries) → unblocks 6 indicators
2. Service frequency (station-level, peak/off-peak) → unblocks 3 indicators
3. Ridership (station-level, daily average) → unblocks 2 indicators
4. LGD spatial boundaries → unblocks 1 indicator

**Recommended Action:**
1. Prioritize population and service frequency data acquisition
2. Follow data acquisition workflow (Section 6.2)
3. Use fallback strategies only if primary sources unavailable
4. Document all data provenance, limitations, and confidence levels

**Expected Outcome:** Transform M4 from "geographic spacing analysis" → "evidence-based infrastructure gap prioritization with population and service quality context"

---

**Document Status:** ✅ COMPLETE  
**Next Action:** Initiate data acquisition for population and service frequency  
**Report Generated:** 2026-09-29  
**Linked Report:** `local_rail_m4_gap_analysis.md`
