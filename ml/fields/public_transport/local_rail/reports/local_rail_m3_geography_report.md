# LOCAL RAIL M3 — Geography Report

**Domain:** Local Rail (Suburban Railway Systems)  
**Milestone:** M3 — Geography, Population & Accessibility  
**Report Date:** 2026-09-29  
**System:** Mumbai Suburban Railway

---

## Executive Summary

This report documents the geography layer investigation for Mumbai Suburban Railway. The primary finding is that **LGD (Local Government Directory) geography data contains hierarchical codes and relationships ONLY** — no spatial boundary polygons are available in the repository.

**Critical Finding:** Station-to-geography spatial joins are **BLOCKED** due to missing boundary geometry. Only theoretical geographic accessibility (buffer analysis) is possible.

---

## Geography Data Investigation

### LGD Geography Files Investigated

| Geography Level | File | Records | Mumbai Records | Geometry Available | Status |
|----------------|------|---------|----------------|-------------------|--------|
| **States** | `states_clean.csv` | 36 | N/A | ✗ | CODES_ONLY |
| **Districts** | `districts_clean.csv` | 784 | 36 | ✗ | CODES_ONLY |
| **Subdistricts** | `subdistricts_clean.csv` | 7,092 | N/A | ✗ | CODES_ONLY |
| **ULBs** | `ulbs_clean.csv` | 5,051 | 422 | ✗ | CODES_ONLY |
| **Wards (Maharashtra)** | `wards_maharashtra_clean.csv` | 7,256 | 0 | ✗ | CODES_ONLY |
| **Wards (All States)** | `wards_all_available_clean.csv` | 28,837 | 0 | ✗ | CODES_ONLY |

### Key Findings

1. **All 6 geography files exist** and contain LGD codes, names, and hierarchical relationships
2. **ZERO files contain spatial geometry** (no WKT, GeoJSON, coordinates, or polygon data)
3. **422 ULB records** exist for Maharashtra (includes Mumbai and surrounding regions)
4. **36 district records** exist for Maharashtra
5. **Wards:** Maharashtra ward dataset exists (7,256 records) but Mumbai-specific ward count is 0 (likely classification issue or Mumbai wards coded differently)

### What the LGD Data Contains

**✓ Available:**
- State codes + names (e.g., `state_code=27`, `state_name=Maharashtra`)
- District codes + names (e.g., `district_code=490`, `district_name=Mumbai`)
- ULB codes + names (e.g., `local_body_code=250956`, `local_body_name=Greater Mumbai`)
- Ward codes + names (for Maharashtra, Karnataka, Tamil Nadu, Delhi)
- Hierarchical relationships (ward → ULB → district → state)
- Census 2011 codes (where available)

**✗ NOT Available:**
- Latitude/longitude coordinates
- Boundary polygons (WKT, GeoJSON, Shapefile)
- Centroid coordinates
- Bounding boxes
- Spatial geometry of any kind

---

## Boundary Geometry Search

### Sources Investigated

| Source | Format | Status | Notes |
|--------|--------|--------|-------|
| **LGD Geography Files** | CSV | CODES_ONLY | No spatial data |
| **Repository GeoJSON Files** | GeoJSON | NOT_FOUND | No Mumbai boundary files |
| **Repository Shapefiles** | .shp | NOT_FOUND | No boundary shapefiles |
| **Repository KML Files** | KML | NOT_FOUND | Only station/line KML (not boundaries) |
| **data.gov.in** | Various | NOT_INVESTIGATED | External source, not in repository |
| **Bhuvan (ISRO)** | GeoTIFF/WMS | NOT_INVESTIGATED | External source, not in repository |
| **Maharashtra Open Data** | Various | NOT_INVESTIGATED | External source, not in repository |

### Conclusion

**No spatial boundary geometry exists in the repository** for:
- Mumbai city boundaries
- Mumbai metropolitan region boundaries
- Maharashtra district boundaries
- ULB (Urban Local Body) boundaries
- Ward boundaries

**Impact:** Spatial joins (station → ward, station → ULB, station → district) are **BLOCKED**.

---

## Mumbai Geography Context

### Expected Geography Hierarchy

```
Maharashtra (State)
├── Mumbai Suburban (District)
│   └── Greater Mumbai Municipal Corporation (ULB)
│       └── Wards 1–227 (Administrative Wards)
├── Thane (District)
│   ├── Thane Municipal Corporation (ULB)
│   ├── Navi Mumbai Municipal Corporation (ULB)
│   └── Other ULBs
└── Raigad (District)
    └── Various ULBs (Panvel, Karjat, Khopoli areas)
```

### Mumbai Suburban Railway Coverage

The 106 stations span **3 districts**:
1. **Mumbai Suburban District** — Churchgate, Bandra, Andheri, Borivali, Virar (Western); CSMT, Kurla, Ghatkopar (Central/Harbour)
2. **Thane District** — Thane, Dombivili, Kalyan, Navi Mumbai (Central + Trans-Harbour)
3. **Raigad District** — Panvel, Karjat, Khopoli (Central Line southern terminus)

**Without boundary polygons**, we cannot definitively assign each station to its district/ULB/ward.

---

## Station-to-Geography Join Status

### Attempted Joins

| Join Type | Status | Reason |
|-----------|--------|--------|
| **Station → Ward** | BLOCKED | No ward boundary polygons |
| **Station → ULB** | BLOCKED | No ULB boundary polygons |
| **Station → District** | BLOCKED | No district boundary polygons |
| **Station → State** | TRIVIAL | All Mumbai stations in Maharashtra (known) |

### Manual Assignment (Not Implemented)

**Possible Approach (Not Executed):**
- Manually assign well-known stations to districts (e.g., Churchgate → Mumbai, Thane → Thane, Panvel → Raigad)
- Use station names to infer ULB (e.g., "Navi Mumbai" in name → Navi Mumbai Municipal Corporation)

**Reason Not Implemented:**
- M3 task requires **spatial joins** based on coordinate-in-polygon tests, not name matching
- Manual assignment prone to errors (e.g., Kalyan station location might span multiple ULB boundaries)
- Would violate data integrity principle (no fabrication, explicit BLOCKED status better than guessed assignments)

---

## Geographic Accessibility Analysis

### Theoretical Catchments Created

Despite missing boundaries, **theoretical geographic accessibility** was calculated using station coordinate buffers:

| Buffer Distance | Stations | Total Coverage Area | Network Length | Type |
|----------------|----------|---------------------|----------------|------|
| **500 m** | 106 | 83.12 km² | 307.46 km | Theoretical |
| **1 km** | 106 | 332.47 km² | 307.46 km | Theoretical |
| **2 km** | 106 | 1,329.90 km² | 307.46 km | Theoretical |

**Methodology:**
1. Load 106 Mumbai station coordinates (EPSG:4326)
2. Project to UTM Zone 43N (EPSG:32643) for accurate meter-based buffers
3. Create circular buffers of 500m, 1km, 2km radius around each station
4. Calculate total coverage area
5. Reproject to EPSG:4326 and save as GeoJSON

**Files Created:**
- `mumbai_station_catchments_500m.geojson` (106 polygons)
- `mumbai_station_catchments_1000m.geojson` (106 polygons)
- `mumbai_station_catchments_2000m.geojson` (106 polygons)

---

## Coverage Area Analysis

### 500m Catchment (Walking Distance)
- **Total Area:** 83.12 km²
- **Interpretation:** Area within 5-minute walk (~500m) of a suburban railway station
- **Typical Use:** Primary catchment for daily commuters

### 1km Catchment (Cycling/Auto Distance)
- **Total Area:** 332.47 km²
- **Interpretation:** Area within ~10-minute cycle or auto-rickshaw ride
- **Typical Use:** Secondary catchment, feeder transport required

### 2km Catchment (Bus/Auto Distance)
- **Total Area:** 1,329.90 km²
- **Interpretation:** Area accessible via bus/auto (15-20 minute ride)
- **Typical Use:** Extended catchment, multimodal trips

### Coverage Context

**Mumbai Metropolitan Region Total Area:** ~4,355 km² (approx.)  
**2km Catchment Coverage:** 1,329.90 km² = **30.5% of MMR area** (theoretical)

**IMPORTANT NOTE:** This is **overlap-inclusive** (catchments from adjacent stations overlap). Actual unique coverage area would be lower when overlaps are dissolved.

---

## Accessibility Limitations

### What the Catchment Analysis Shows

✓ **Geographic proximity** — Which areas are within X meters of a station (straight-line distance)  
✓ **Network coverage** — Spatial distribution of station access points  
✓ **Theoretical maximum reach** — If walking/cycling/bus were unobstructed  

### What the Catchment Analysis Does NOT Show

✗ **Actual transit accessibility** — Requires service frequency, operating hours, peak/off-peak schedules  
✗ **Multimodal connectivity** — Requires bus/metro feeder network data  
✗ **Physical barriers** — Rivers, highways, railway lines that block pedestrian access  
✗ **Population served** — Requires population data + boundary polygons  
✗ **Demand patterns** — Requires ridership data  
✗ **Service quality** — Requires frequency, reliability, crowding data  

**Critical Distinction:**
- **Geographic accessibility** (calculated here) = proximity to infrastructure
- **Transit accessibility** (not calculable) = actual ability to use the service based on schedules, routes, and capacity

---

## Data Gaps Summary

### Blocked Analyses

| Analysis | Status | Blocker | Impact |
|----------|--------|---------|--------|
| **Station-to-ward join** | BLOCKED | No ward polygons | Cannot determine which ward each station serves |
| **Station-to-ULB join** | BLOCKED | No ULB polygons | Cannot calculate stations per ULB |
| **Station-to-district join** | BLOCKED | No district polygons | Cannot compare districts by rail coverage |
| **Population per station** | BLOCKED | No boundaries + no population | Cannot estimate demand |
| **Stations per 100k population** | BLOCKED | No population data | Cannot normalize coverage by population |
| **Underserved area identification** | BLOCKED | No boundaries + population | Cannot map gaps |
| **Catchment population** | BLOCKED | No population polygons | Cannot calculate people within 500m/1km/2km |

### Available Analyses

| Analysis | Status | Notes |
|----------|--------|-------|
| **Station coordinates** | ✓ COMPLETE | 106 stations, 100% valid |
| **Network length** | ✓ COMPLETE | 307.46 km |
| **Station spacing** | ✓ COMPLETE | Median 1,759 m |
| **Geographic catchments** | ✓ COMPLETE | 500m, 1km, 2km buffers |
| **Coverage area (theoretical)** | ✓ COMPLETE | 83–1,330 km² depending on buffer |

---

## Recommendations

### High Priority — Acquire Spatial Boundaries
1. **Survey of India:** Official boundary datasets (may require approval/license)
2. **Maharashtra Remote Sensing Application Centre (MRSAC):** State-level GIS data
3. **Brihanmumbai Municipal Corporation (BMC) GIS:** Ward/ULB boundaries for Greater Mumbai
4. **DataMeet India:** Community-sourced boundary datasets (verify license compatibility)
5. **OpenStreetMap:** Extract admin boundaries (check completeness and accuracy)

### Medium Priority — Acquire Population Data
6. **Census 2011 Digital Library:** Download district/ULB population tables
7. **Census 2021 (when released):** Latest population counts
8. **Maharashtra Directorate of Economics and Statistics:** State population estimates

### Low Priority — Alternative Approaches
9. **Manual Name-Based Assignment:** Assign stations to districts/ULBs based on station names (error-prone, not spatial)
10. **OSM Nominatim Reverse Geocoding:** Query OpenStreetMap for admin boundaries at each station coordinate (dependent on OSM completeness)
11. **Google Maps API Reverse Geocoding:** Commercial API for admin boundaries (requires API key, rate limits)

---

## M3 Geography Status

| Component | Status | Notes |
|-----------|--------|-------|
| **LGD Data** | ✓ AVAILABLE | Codes only, no geometry |
| **Spatial Boundaries** | ✗ UNAVAILABLE | No polygons found |
| **Population Data** | ✗ UNAVAILABLE | No census data found |
| **Station Coordinates** | ✓ COMPLETE | 106 valid stations |
| **Geographic Catchments** | ✓ COMPLETE | 500m, 1km, 2km buffers |
| **Station-Geography Join** | ✗ BLOCKED | No boundaries |
| **Population Catchment** | ✗ BLOCKED | No boundaries + no population |

---

## Conclusion

Mumbai Suburban Railway M3 geography analysis is **PARTIALLY COMPLETE**. Theoretical geographic accessibility (catchment buffers) was successfully calculated, but **all population-based and boundary-based analyses are BLOCKED** due to missing spatial geometry and population data in the repository.

**Key Limitation:** Without boundary polygons, we cannot perform the spatial joins necessary to connect infrastructure (stations) to administrative geography (wards, ULBs, districts) or population data.

**Path Forward:** M3 documented what data exists and what is missing. Future work requires acquiring official spatial boundaries and population datasets before population-based accessibility analysis can proceed.

---

**Report Author:** Kiro AI Agent  
**Report Date:** 2026-09-29  
**Data Sources:** LGD (codes only), BMC OpenCity.in (station coordinates)  
**Next Steps:** Create M3 accessibility and audit reports
