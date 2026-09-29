# Local Rail Data Collection Report

**Date**: 2026-09-29  
**Phase**: Step 1 - Raw Data Collection + Source Verification  
**Status**: PARTIAL

---

## Executive Summary

Collected raw data for **2 of 5** target suburban railway systems with machine-readable data:
- ✅ **Mumbai**: Complete (KML lines + stations)
- ⚠️ **Chennai**: Community GTFS (excludes suburban rail)
- ❌ **Kolkata**: No machine-readable data found
- ❌ **Hyderabad MMTS**: No machine-readable data found  
- ❌ **Pune**: No machine-readable data found

**Critical Finding**: Indian Railways does not publish official machine-readable GTFS/GIS data for suburban railway systems (except through civic open data portals for Mumbai).

---

## Mumbai Suburban Railway ✅ VERIFIED

### Datasets Found
1. **Mumbai Suburban Lines KML**
2. **Mumbai Suburban Stations KML**

### Source
- **Publisher**: BMC (Brihanmumbai Municipal Corporation) via OpenCity.in
- **URL**: https://data.opencity.in/dataset/mumbai-suburban-network-2025
- **Type**: Civic Open Data Portal
- **License**: Public Domain
- **Official Status**: Civic Open Data (not directly from Central/Western Railway)

### Format
- **Lines**: KML (106 placemarks with line geometry)
- **Stations**: KML (106 placemarks with coordinates)

### Coverage
- Western Railway suburban
- Central Railway suburban
- Harbour Line
- Trans-Harbour Line (if included in 2025 dataset)

### Downloaded Files
```
data/raw/local_rail/mumbai/mumbai_suburban_lines.kml (185,829 bytes)
data/raw/local_rail/mumbai/mumbai_suburban_stations.kml (55,061 bytes)
```

### Validation
- ✅ Valid XML/KML
- ✅ 106 placemarks in lines file
- ✅ 106 placemarks in stations file
- ✅ All placemarks have coordinates

### Limitations
- No timetable/schedule data
- No train service information
- No ridership data
- No service frequency
- Station/line metadata requires extraction from KML extended data

---

## Chennai Suburban Railway ⚠️ COMMUNITY_SECONDARY

### Datasets Found
1. **Chennai Unified GTFS** (Community-collected)

### Source
- **Publisher**: UngalSoththu (Chennai civic tech community)
- **URL**: https://github.com/ungalsoththu/ChennaiGTFS
- **Type**: Community Repository
- **License**: ODbL (Open Database License)
- **Official Status**: **COMMUNITY_SECONDARY** (not official Indian Railways)

### Format
- **GTFS ZIP** (9.09 MB)
- Contains: MTC buses + CMRL metro

### Coverage
**CRITICAL LIMITATION**: Repository documentation explicitly states:
> "Known gaps: No suburban rail — Chennai's Southern Railway suburban system (MRTS + main line) has zero GTFS data. This is the biggest gap."

This GTFS **DOES NOT INCLUDE** Chennai suburban railway (Southern Railway EMU services).

### Downloaded Files
```
data/raw/local_rail/chennai/chennai_suburban_gtfs_community.zip (9,089,658 bytes)
```

### What's Missing
- ❌ Chennai suburban railway stations
- ❌ Chennai suburban railway routes
- ❌ Chennai suburban railway timetables
- ❌ Southern Railway EMU services

### Official Source Status
**Southern Railway** (https://sr.indianrailways.gov.in/):
- ✅ Website accessible
- ❌ No machine-readable suburban timetable data
- ❌ No GTFS feed
- ❌ No KML/GeoJSON station data
- ⚠️ Timetable information may exist as PDF/HTML: **MANUAL_REQUIRED**

### Notes
The community GTFS is high-quality for MTC/CMRL but **does not solve the suburban rail data gap**. Official Southern Railway suburban data remains unavailable in machine-readable format.

---

## Kolkata Suburban Railway ❌ UNAVAILABLE

### Search Conducted
- ✅ Eastern Railway official site: https://er.indianrailways.gov.in/
- ✅ South Eastern Railway official site: https://ser.indianrailways.gov.in/
- ✅ data.gov.in searched
- ✅ OpenCity.in searched
- ✅ IUDX searched

### Datasets Found
**NONE** - No machine-readable suburban railway data found.

### What Exists
- Wikipedia documentation of network
- Third-party mobile apps (non-authoritative)
- Community transit maps

### What's Missing
- ❌ Station coordinates
- ❌ Route geometry
- ❌ Official timetables (machine-readable)
- ❌ Service frequency
- ❌ Ridership data

### Official Source Status
**Eastern Railway / South Eastern Railway**:
- ✅ Websites accessible
- ❌ No GTFS feed
- ❌ No KML/GeoJSON data
- ❌ No suburban-specific machine-readable data

### Status
**UNAVAILABLE** - Would require either:
1. Manual extraction from scattered sources
2. Official data release from Eastern/South Eastern Railway
3. Crowdsourced community data collection

---

## Hyderabad MMTS ❌ UNAVAILABLE

### Search Conducted
- ✅ South Central Railway official site: https://scr.indianrailways.gov.in/
- ✅ data.gov.in searched
- ✅ OpenCity.in searched (found Hyderabad Metro, NOT MMTS)
- ✅ IUDX searched

### Datasets Found
**NONE** - No official machine-readable MMTS data found.

### Third-Party Sources Identified
1. **mmtstrains.in** - Timetable aggregator website
2. **mmtstrains.com** - Another timetable aggregator
3. Scribd documents with timetable PDFs

**Status**: All third-party, non-authoritative sources. **DEFERRED** pending verification.

### What's Missing
- ❌ Official MMTS station coordinates
- ❌ MMTS route geometry
- ❌ Official MMTS timetable (machine-readable)
- ❌ Service frequency
- ❌ Ridership data

### IMPORTANT DISTINCTION
**Hyderabad Metro** (HMRL): ✅ Has official GTFS (collected in Metro phase)  
**Hyderabad MMTS** (SCR suburban rail): ❌ No official machine-readable data

These are **separate systems**. Metro data cannot be used for MMTS analysis.

### Official Source Status
**South Central Railway**:
- ✅ Website accessible
- ❌ No MMTS-specific data portal
- ❌ No GTFS feed
- ❌ No KML/GeoJSON data

### Status
**UNAVAILABLE** - Would require either:
1. Manual extraction from third-party aggregators (with verification)
2. Official data release from South Central Railway
3. Field survey/crowdsourcing

---

## Pune Suburban Railway ❌ UNAVAILABLE

### Search Conducted
- ✅ Central Railway official site: https://cr.indianrailways.gov.in/
- ✅ data.gov.in searched
- ✅ OpenCity.in searched
- ✅ IUDX searched

### Datasets Found
**NONE** - No official machine-readable data found.

### Third-Party Sources Identified
1. **ixigo.com** - Train timetable aggregator (Pune-Lonavala EMU trains listed)
2. **indianrailways.info** - Non-official train info site
3. Wikipedia - Route documentation

**Status**: All third-party. Not authoritative sources. **DEFERRED**.

### System Documentation
From Wikipedia and third-party sources:
- **Routes**: Pune Junction–Lonavala (63 km), Shivaji Nagar–Talegaon
- **Service**: ~17 EMU trains on Pune-Lonavala route
- **Operator**: Central Railway
- **Introduced**: 1978 (EMU service)

### What's Missing
- ❌ Official station coordinates
- ❌ Route geometry
- ❌ Official timetable (machine-readable)
- ❌ Service frequency
- ❌ Ridership data
- ❌ Stop-level schedules

### Official Source Status
**Central Railway**:
- ✅ Website accessible
- ❌ No Pune suburban data portal
- ❌ No GTFS feed
- ❌ No KML/GeoJSON data

### Status
**UNAVAILABLE** - Would require either:
1. Manual extraction from third-party aggregators (with verification)
2. Official data release from Central Railway
3. Field survey at Pune Junction/Lonavala stations

---

## Source Verification Summary

| System | Dataset | Publisher | Format | Official | Machine-Readable | Status |
|--------|---------|-----------|--------|----------|------------------|--------|
| **Mumbai** | Lines + Stations | BMC via OpenCity | KML | Civic Open Data | ✅ Yes | ✅ VERIFIED |
| **Chennai** | Unified GTFS | UngalSoththu | GTFS ZIP | ❌ Community | ✅ Yes | ⚠️ EXCLUDES SUBURBAN RAIL |
| **Chennai** | SR Timetable | Southern Railway | PDF/HTML | ✅ Official | ⚠️ Partial | ⚠️ MANUAL_REQUIRED |
| **Kolkata** | ER/SER Network | Eastern/SE Railway | N/A | ✅ Official | ❌ No | ❌ UNAVAILABLE |
| **Hyderabad** | MMTS | South Central Railway | N/A | ✅ Official | ❌ No | ❌ UNAVAILABLE |
| **Pune** | EMU Service | Central Railway | N/A | ✅ Official | ❌ No | ❌ UNAVAILABLE |

---

## Raw Files Collected

### Successfully Downloaded (2 systems, 3 files)
```
data/raw/local_rail/
├── mumbai/
│   ├── mumbai_suburban_lines.kml          (185,829 bytes, 106 placemarks)
│   └── mumbai_suburban_stations.kml       (55,061 bytes, 106 placemarks)
├── chennai/
│   └── chennai_suburban_gtfs_community.zip (9,089,658 bytes, MTC+CMRL only)
├── kolkata/                                (empty - no data found)
├── hyderabad/                              (empty - no data found)
└── pune/                                   (empty - no data found)
```

---

## Missing Data Inventory

### Station Coordinates
- ✅ Mumbai: Available (106 stations in KML)
- ❌ Chennai Suburban: NOT AVAILABLE
- ❌ Kolkata: NOT AVAILABLE
- ❌ Hyderabad MMTS: NOT AVAILABLE
- ❌ Pune: NOT AVAILABLE

### Timetable/Schedule
- ❌ Mumbai: NOT AVAILABLE
- ⚠️ Chennai: May exist as PDF (MANUAL_REQUIRED)
- ❌ Kolkata: NOT AVAILABLE
- ⚠️ Hyderabad: Third-party aggregators exist (DEFERRED)
- ⚠️ Pune: Third-party aggregators exist (DEFERRED)

### Ridership
- ❌ Mumbai: NOT AVAILABLE
- ❌ Chennai: NOT AVAILABLE
- ❌ Kolkata: NOT AVAILABLE
- ❌ Hyderabad: NOT AVAILABLE
- ❌ Pune: NOT AVAILABLE

### Network Geometry
- ✅ Mumbai: Available (line geometry in KML)
- ❌ Chennai: NOT AVAILABLE
- ❌ Kolkata: NOT AVAILABLE
- ❌ Hyderabad: NOT AVAILABLE
- ❌ Pune: NOT AVAILABLE

### Service Frequency
- ❌ All systems: NOT AVAILABLE

---

## Access-Blocked Sources

**NONE** - No sources requiring API keys, login, or CAPTCHA were encountered.

The issue is not access restriction but **absence of published machine-readable data**.

---

## Manual-Required Sources

1. **Chennai Suburban Railway Timetable**
   - **Source**: Southern Railway official website / PDF timetables
   - **Status**: MANUAL_REQUIRED
   - **Reason**: Timetable information may exist in PDF/HTML format but not in machine-readable GTFS

2. **Kolkata Suburban Railway**
   - **Status**: Would require manual field survey or community crowdsourcing
   - **Reason**: No official machine-readable data published

3. **Hyderabad MMTS**
   - **Third-party aggregators**: mmtstrains.in, scribd PDFs
   - **Status**: DEFERRED (requires verification of accuracy)
   - **Reason**: Not official sources; would need validation against SCR official information

4. **Pune Suburban Railway**
   - **Third-party aggregators**: ixigo.com listings
   - **Status**: DEFERRED (requires verification)
   - **Reason**: Not official sources; would need validation against Central Railway

---

## Critical Findings

### Indian Railways Suburban Data Gap
**Indian Railways does NOT publish official machine-readable data for suburban railway systems** in GTFS, KML, or GeoJSON formats.

This is in stark contrast to:
- ✅ **Metro systems**: Hyderabad Metro, Bengaluru Metro have official GTFS
- ✅ **Civic open data**: Mumbai gets KML through BMC/OpenCity
- ❌ **Suburban rail**: Zero official machine-readable datasets across all 5 systems

### Data Level Comparison

| System Type | Example | Official Machine-Readable Data |
|-------------|---------|-------------------------------|
| Metro (Urban Transit Authority) | Hyderabad Metro (HMRL) | ✅ Yes (GTFS) |
| Suburban Rail (Indian Railways) | Chennai Suburban (Southern Railway) | ❌ No |
| Civic Open Data Portal | Mumbai Suburban (BMC via OpenCity) | ✅ Yes (KML) |

**Implication**: Suburban rail analysis will have severe data limitations compared to Metro analysis.

---

## Recommendations

### Immediate Actions (Step 1 Complete)
1. ✅ Mumbai: Proceed with KML data (stations + lines available)
2. ⚠️ Chennai: Mark suburban rail as DATA_GAP; community GTFS cannot substitute
3. ❌ Kolkata: Mark as UNAVAILABLE; defer until official data available
4. ❌ Hyderabad MMTS: Mark as UNAVAILABLE; third-party sources require validation
5. ❌ Pune: Mark as UNAVAILABLE; defer until official data available

### Future Steps (Beyond Step 1)
1. **Engage with Indian Railways**: Request official GTFS/GIS data publication for suburban systems
2. **Community crowdsourcing**: If official data unavailable, consider structured community data collection with validation protocols
3. **Manual extraction**: For Chennai, consider extracting Southern Railway timetable from PDFs if needed
4. **OSM supplementary**: Use OpenStreetMap railway data as supplementary source (ONLY for geometry, NOT for schedules/ridership)

### Data Availability by Analysis Phase

| Analysis Phase | Mumbai | Chennai | Kolkata | Hyderabad | Pune |
|----------------|--------|---------|---------|-----------|------|
| Station mapping | ✅ Yes | ❌ No | ❌ No | ❌ No | ❌ No |
| Network topology | ✅ Yes | ❌ No | ❌ No | ❌ No | ❌ No |
| Timetable analysis | ❌ No | ⚠️ Manual | ❌ No | ⚠️ 3rd-party | ⚠️ 3rd-party |
| Ridership analysis | ❌ No | ❌ No | ❌ No | ❌ No | ❌ No |
| Accessibility | ✅ Partial | ❌ No | ❌ No | ❌ No | ❌ No |

---

## Step 1 Status: PARTIAL COMPLETION

### Completed ✅
- [x] Mumbai searched and collected
- [x] Chennai searched (community GTFS collected with limitations documented)
- [x] Kolkata searched (no data found, documented)
- [x] Hyderabad MMTS searched (no data found, documented)
- [x] Pune searched (no data found, documented)
- [x] Raw files preserved
- [x] Source URLs recorded
- [x] Publishers recorded
- [x] Formats recorded
- [x] Machine-readable status recorded
- [x] Official status recorded
- [x] License recorded
- [x] No cleaning performed
- [x] No EDA performed
- [x] No geospatial analysis performed
- [x] No LGD mapping performed
- [x] No population join performed
- [x] No gap scoring performed
- [x] Bus files untouched
- [x] Metro files untouched
- [x] National Highways files untouched
- [x] Geography files untouched

### Collection Status
- **Machine-readable data**: 2/5 systems (40%)
- **Complete coverage**: 1/5 systems (20%) - Mumbai only
- **Partial coverage**: 1/5 systems (20%) - Chennai (community data, excludes suburban rail)
- **No data**: 3/5 systems (60%) - Kolkata, Hyderabad MMTS, Pune

### Overall Assessment
**Step 1 is TECHNICALLY COMPLETE** (search performed for all systems) but **DATA INCOMPLETE** (only 2/5 systems have usable machine-readable data).

Proceeding to cleaning/analysis will only be possible for:
- ✅ **Mumbai**: Station + network geometry available
- ⚠️ **Chennai**: Community GTFS available but excludes suburban rail
- ❌ **Kolkata, Hyderabad MMTS, Pune**: Insufficient data for analysis

---

## Next Steps

**STOP HERE** - Awaiting instruction:
> "START LOCAL RAIL CLEANING"

Do NOT proceed with cleaning until explicitly instructed.

---

**Report Complete**: 2026-09-29  
**Phase**: Step 1 - Data Collection Only  
**Status**: PARTIAL (2/5 systems with machine-readable data)
