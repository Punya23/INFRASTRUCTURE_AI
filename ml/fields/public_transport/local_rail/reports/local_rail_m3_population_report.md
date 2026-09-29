# LOCAL RAIL M3 — Population Report

**Domain:** Local Rail (Suburban Railway Systems)  
**Milestone:** M3 — Population & Demand Analysis  
**Report Date:** 2026-09-29  
**System:** Mumbai Suburban Railway

---

## Executive Summary

This report documents the population data investigation for Mumbai Suburban Railway catchment analysis. The primary finding is that **NO population data exists in the repository** — neither Census data nor alternative population estimates were found.

**Status:** All population-based analyses are **BLOCKED**.

---

## Population Data Investigation

### Sources Searched

| Source | Location | Format | Status | Notes |
|--------|----------|--------|--------|-------|
| **Census Files** | `data/raw/census/` | CSV/Excel | NOT_FOUND | Directory does not exist |
| **Census Files** | `data/processed/census/` | CSV | NOT_FOUND | Directory does not exist |
| **Geography Population** | `ml/fields/geography/data/raw/population/` | CSV/Excel | NOT_FOUND | Directory does not exist |
| **Geography Population** | `ml/fields/geography/data/processed/population/` | CSV | NOT_FOUND | Directory does not exist |
| **LGD Geography Files** | `ml/fields/geography/data/processed/*.csv` | CSV | ✓ FOUND | **NO population columns** present |
| **Ad-hoc Population Files** | Repository search | Various | NOT_FOUND | No files with "population" or "census" in name |

### LGD Geography Files — Population Column Check

| File | Population Columns | Status |
|------|-------------------|--------|
| `states_clean.csv` | None | No population data |
| `districts_clean.csv` | None | No population data |
| `subdistricts_clean.csv` | None | No population data |
| `ulbs_clean.csv` | `census_2011_code` (code only, not population) | No population data |
| `wards_maharashtra_clean.csv` | None | No population data |
| `wards_all_available_clean.csv` | None | No population data |

**Finding:** LGD geography files contain Census 2011 **codes** (for matching purposes) but no actual **population counts**.

---

## Expected Population Data

### For Mumbai Suburban Railway Analysis

#### Ward-Level Population (Ideal)
- **Geography:** Mumbai Municipal Corporation (BMC) wards (227 wards)
- **Population:** Census 2011 or 2021 ward-level counts
- **Use Case:** Precise catchment population (intersect 500m/1km/2km buffers with ward polygons)
- **Status:** UNAVAILABLE

#### ULB-Level Population
- **Geography:** Greater Mumbai ULB + Thane ULB + Navi Mumbai ULB + other Mumbai MMR ULBs
- **Population:** Census 2011/2021 ULB-level counts
- **Use Case:** Rough catchment population (assign stations to ULBs, aggregate)
- **Status:** UNAVAILABLE

#### District-Level Population
- **Geography:** Mumbai Suburban District + Thane District + Raigad District
- **Population:** Census 2011/2021 district-level counts
- **Use Case:** Very rough population estimates (least precise)
- **Status:** UNAVAILABLE

---

## Census Data Context

### Census 2011 (Most Recent Published)
- **Release Year:** 2011 (15 years old as of 2026)
- **Availability:** Publicly available via Census of India website
- **Format:** PDF reports + Excel tables (downloadable)
- **Geographic Levels:** State, District, Sub-district, ULB, Ward (varies by state)

**Not Found in Repository:** Census 2011 data must be downloaded and processed separately.

### Census 2021 (Expected but Delayed)
- **Scheduled Release:** 2021
- **Actual Status:** Delayed (as of 2026, preliminary results may be available but full data unpublished)
- **Availability:** TBD

---

## Blocked Analyses

Due to missing population data, the following analyses are **BLOCKED**:

### 1. Catchment Population
**Goal:** Calculate population within 500m, 1km, 2km of each station

**Method (If Data Available):**
```
1. Load population polygons (wards/ULBs with population counts)
2. Intersect with station catchment buffers (500m/1km/2km)
3. Calculate proportional population in each intersection
4. Sum population per station
```

**Status:** BLOCKED  
**Blocker:** No population polygons OR counts available

---

### 2. Stations per 100k Population
**Goal:** Normalize station count by catchment population

**Formula (If Data Available):**
```
Stations per 100k = (Total Stations / Catchment Population) × 100,000
```

**Example (Hypothetical):**
- If 2km catchment covers 10 million people
- 106 stations / 10,000,000 × 100,000 = **1.06 stations per 100k**

**Status:** BLOCKED  
**Blocker:** No catchment population available

---

### 3. Population per Station
**Goal:** Calculate average population served per station

**Formula (If Data Available):**
```
Population per station = Catchment Population / Total Stations
```

**Example (Hypothetical):**
- If 500m catchment covers 3 million people
- 3,000,000 / 106 stations = **28,302 people per station**

**Status:** BLOCKED  
**Blocker:** No catchment population available

---

### 4. Underserved Population Identification
**Goal:** Identify areas with high population but no/low rail access

**Method (If Data Available):**
```
1. Identify high-population areas (e.g., >10k people per km²)
2. Calculate distance to nearest station
3. Flag areas >2km from any station
4. Prioritize by population density
```

**Status:** BLOCKED  
**Blocker:** No population data OR boundaries available

---

### 5. Demand Estimation
**Goal:** Estimate potential ridership based on catchment population

**Method (If Data Available):**
```
1. Calculate catchment population (500m preferred)
2. Apply mode share assumption (e.g., 30% of population uses suburban rail)
3. Estimate daily trips per person (e.g., 1.5 trips/day)
4. Calculate station-level demand
```

**Example (Hypothetical):**
- Station catchment: 50,000 people
- Mode share: 30% → 15,000 potential users
- Trips/day: 1.5 → 22,500 daily trips per station

**Status:** BLOCKED  
**Blocker:** No population data + no actual ridership for validation

---

### 6. Population Density Analysis
**Goal:** Compare station density to population density

**Method (If Data Available):**
```
1. Calculate population density by area (people per km²)
2. Calculate station density (stations per km²)
3. Identify mismatches (high population, low stations)
```

**Status:** BLOCKED  
**Blocker:** No population data

---

## Alternative Population Sources (Not in Repository)

### Official Sources
1. **Census of India Digital Library**
   - URL: https://censusindia.gov.in/
   - Data: Census 2011 tables (Excel/PDF)
   - License: Open Government Data (OGD)
   - Effort: Download + clean + geocode

2. **Office of the Registrar General & Census Commissioner**
   - URL: https://censusindia.gov.in/
   - Data: Ward/ULB-level population tables
   - Format: Excel downloads

3. **Maharashtra Directorate of Economics and Statistics**
   - URL: https://mahades.maharashtra.gov.in/
   - Data: State population estimates (may have district/ULB breakdowns)

### Alternative Sources
4. **WorldPop / LandScan**
   - Data: Gridded population estimates (100m–1km resolution)
   - Format: GeoTIFF rasters
   - License: Open (CC BY 4.0)
   - Limitation: Modeled estimates, not Census-official

5. **Facebook Population Density Maps**
   - Data: High-resolution population grids
   - Format: GeoTIFF
   - License: CC BY (archived project)
   - Limitation: Based on 2015–2020 data

6. **OpenStreetMap + Humanitarian Data Exchange (HDX)**
   - Data: Population estimates at admin levels
   - Format: CSV/GeoJSON
   - Limitation: Aggregated from various sources, may not match Census

---

## Recommendations

### High Priority — Acquire Official Census Data
1. **Download Census 2011 ward-level population** for Mumbai, Thane, Navi Mumbai
2. **Download Census 2011 ULB-level population** for Maharashtra
3. **Download Census 2011 district-level population** for Maharashtra
4. **Clean and standardize** to match LGD codes in `ml/fields/geography/`

**Effort:** 1–2 days (download + clean + document)  
**Benefit:** Official, authoritative population data for catchment analysis

### Medium Priority — Acquire Spatial Boundaries + Population
5. **Acquire ward polygons** with Census 2011 population (from Maharashtra GIS or DataMeet)
6. **Acquire ULB polygons** with Census 2011 population
7. **Perform spatial intersections** with station catchments

**Effort:** 3–5 days (acquire + validate + spatial join)  
**Benefit:** Precise population-in-catchment calculations

### Low Priority — Alternative Population Estimates
8. **Download WorldPop raster** for Maharashtra (100m resolution)
9. **Extract population within catchments** using zonal statistics
10. **Compare with Census data** (when available) to assess accuracy

**Effort:** 2–3 days (download + process + validate)  
**Benefit:** Approximate population estimates (modeled, not Census-official)

---

## M3 Population Status

| Component | Status | Notes |
|-----------|--------|-------|
| **Census 2011 Data** | ✗ UNAVAILABLE | Not in repository (must download) |
| **Census 2021 Data** | ✗ UNAVAILABLE | Not yet fully published |
| **Ward Population** | ✗ UNAVAILABLE | No data found |
| **ULB Population** | ✗ UNAVAILABLE | No data found |
| **District Population** | ✗ UNAVAILABLE | No data found |
| **Population Polygons** | ✗ UNAVAILABLE | No geometry + no population counts |
| **Catchment Population** | ✗ BLOCKED | Cannot calculate without data |
| **Population-Based Metrics** | ✗ BLOCKED | All analyses blocked |

---

## Comparative Context

### Metro Rail Population Analysis (Example)
**Status:** If Metro M3 was completed with population data, it would include:
- Catchment population per station
- Stations per 100k population
- Underserved area identification
- Demand estimation

**Local Rail Status:** Cannot perform any of the above due to missing data.

### National Highways Population Analysis (Example)
**Status:** If NH M3 included population, it would include:
- Population within X km of highway access points
- Population served by highway network
- Underserved districts

**Local Rail Status:** Same data gap — no population available.

---

## Conclusion

Mumbai Suburban Railway M3 population analysis is **COMPLETELY BLOCKED** due to absence of population data in the repository. No Census 2011, Census 2021, or alternative population sources were found.

**Critical Data Gap:** Without population data:
- Cannot estimate ridership demand
- Cannot identify underserved areas
- Cannot normalize coverage metrics (stations per 100k)
- Cannot prioritize expansion/improvement projects by population need

**Path Forward:** Acquiring Census 2011 ward/ULB-level population data for Mumbai Metropolitan Region is **essential prerequisite** for population-based transit planning analysis.

---

**Report Author:** Kiro AI Agent  
**Report Date:** 2026-09-29  
**Data Sources:** None (population data unavailable)  
**Next Steps:** Create M3 audit report
