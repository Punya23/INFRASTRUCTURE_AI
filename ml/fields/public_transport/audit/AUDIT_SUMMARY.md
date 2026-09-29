# PUBLIC TRANSPORT STATE×MODE AUDIT — QUICK SUMMARY

**Audit Date:** 2026-09-29  
**Type:** Repository Inventory (Inspection Only — NO New Data Collected)  
**Status:** ✅ COMPLETE

---

## STATE × MODE MATRIX (Quick Reference)

| State | Bus | Metro | Local Rail |
|-------|-----|-------|------------|
| **Maharashtra** | MINIMAL (fleet counts only) | MISSING | **SUBSTANTIAL** (Mumbai M1-M4 ✓) |
| **Delhi** | BLOCKED (GTFS exists, CSRF) | BLOCKED (GTFS exists, CSRF) | N/A |
| **Karnataka** | MINIMAL (fleet counts only) | PARTIAL (stations only) | N/A |
| **Tamil Nadu** | MINIMAL (fleet counts only) | PARTIAL (ridership only) | BLOCKED (PDF only) |
| **Telangana** (other) | **SUBSTANTIAL** (full GTFS ✓) | **SUBSTANTIAL** (full GTFS ✓) | MISSING |

---

## WHAT WE HAVE (Repository Assets)

### ✅ COMPLETE (All Stages Done)
1. **Maharashtra Local Rail (Mumbai Suburban):** 106 stations, M1-M4 complete
   - Stations ✓, spacing ✓, catchments ✓, gap analysis ✓ (11 potential gaps)
   - **Blocked:** population, service frequency, ridership

2. **Telangana Bus (TGSRTC):** 5,028 stops, 1,031 routes, full GTFS ✓
   - Cleaning ✓, validation ✓, EDA ✓, geospatial ✓
   - **Not yet done:** catchments, gap analysis

3. **Telangana Metro (Hyderabad HMRL):** 57 stations, 3 lines, full GTFS ✓
   - Cleaning ✓, validation ✓, EDA ✓, fares ✓
   - **Not yet done:** geospatial, gap analysis

### 🟨 PARTIAL (Some Data, Incomplete)
4. **Karnataka Metro (Bengaluru):** 63 stations with coordinates
   - **Missing:** GTFS (no routes/trips/frequencies)

5. **Tamil Nadu Metro (Chennai):** 39 months ridership (system-wide)
   - **Missing:** stations, routes, GTFS

6. **Smart Cities Bus Fleet:** 74 cities including Pune, Nagpur, Bengaluru, Chennai
   - **Only:** fleet counts, terminal/stop counts
   - **Missing:** stop coordinates, routes, GTFS

---

## WHAT WE DON'T HAVE (Critical Gaps)

### 🚫 MISSING (Zero Data)
- All Maharashtra bus operators (MSRTC, BEST Mumbai, PMPML Pune)
- All Maharashtra metro (Mumbai, Pune, Nagpur)
- All Karnataka bus (BMTC Bengaluru)
- All Tamil Nadu bus (MTC Chennai)
- Chennai Metro stations/GTFS (only ridership exists)
- Chennai Suburban Rail stations
- Telangana MMTS (Hyderabad local rail)

### 🔒 BLOCKED (Data Exists But Inaccessible)
- **Delhi Bus + Metro:** Full GTFS exists but CSRF-protected download
  - **Action:** Manual download via browser
- **Chennai Suburban Rail:** Timetable exists but PDF/HTML only
  - **Action:** Manual extraction or find alternate source

### 🌍 MISSING FOR ALL STATES
- **Population data:** No census ward-level with boundaries
- **LGD boundaries:** Codes exist but NO polygon geometries
- **Ridership (station-level):** Only Chennai has system-wide monthly
- **Service frequency:** Only derivable from Telangana GTFS

---

## TOP 10 DATA COLLECTION PRIORITIES

### Tier 1: Unblock Existing Work
1. **Manual download Delhi Bus + Metro GTFS** → Unblocks 2 state×mode combos
2. **Collect population data (Census 2021 or WorldPop)** → Unblocks ALL population analyses
3. **Collect Mumbai Suburban service frequency** → Unblocks Mumbai M4 service indicators
4. **Collect Chennai Metro stations** → Unblocks network analysis (ridership already exists)
5. **Collect LGD spatial boundaries** → Unblocks administrative mapping for ALL systems

### Tier 2: Major City Bus Networks
6. **BEST (Mumbai) Bus GTFS**
7. **BMTC (Bengaluru) Bus GTFS**
8. **MTC (Chennai) Bus GTFS**

### Tier 3: Complete Metro Coverage
9. **Mumbai Metro GTFS** (MMRDA/MML)
10. **Bengaluru Metro GTFS** (stations exist; need service data)

---

## RECORD COUNTS (Repository Totals)

**Bus:**
- 5,028 stops (Telangana only)
- 1,031 routes (Telangana only)
- 74 cities with fleet counts (no coordinates)

**Metro:**
- 120 stations total (57 Hyderabad, 63 Bengaluru)
- 6 routes (3 Hyderabad, 3 Bengaluru lines)
- 39 monthly ridership records (Chennai system-wide)

**Local Rail:**
- 106 stations (Mumbai Suburban only)
- 307.46 km network (Mumbai only)
- 11 potential spacing gaps (Mumbai M4 analysis)

---

## AUDIT OUTPUTS (5 Files)

| File | Rows | Description |
|------|------|-------------|
| `state_mode_dataset_matrix.csv` | 61 | Dataset-level availability matrix |
| `state_mode_processing_matrix.csv` | 15 | Processing stage completion status |
| `state_mode_remaining_work.csv` | 33 | Priority-ordered remaining datasets |
| `state_mode_available_data_summary.md` | — | State-by-state detailed inventory |
| `state_coverage_audit_report.md` | — | Comprehensive audit report (this) |

---

## STATE×MODE COMBINATION COUNTS

**Total Audited:** 15 combinations (4 target states + 1 non-target × 3 modes, minus N/A)

**By Status:**
- **SUBSTANTIAL:** 3 (Mumbai Local Rail, Telangana Bus, Telangana Metro)
- **PARTIAL:** 2 (Bengaluru Metro, Chennai Metro)
- **MINIMAL:** 3 (Maharashtra Bus, Karnataka Bus, Tamil Nadu Bus)
- **BLOCKED:** 3 (Delhi Bus, Delhi Metro, Chennai Local Rail)
- **MISSING:** 3 (Maharashtra Metro, Telangana Local Rail, Pune Suburban)
- **NOT_APPLICABLE:** 2 (Delhi Local Rail, Karnataka Local Rail)

---

## REPOSITORY SAFETY ✅

- ✅ No existing data files modified
- ✅ No existing reports modified
- ✅ No files deleted
- ✅ No national highways files touched
- ✅ Only new audit directory created

**Git Status:** Clean (only new `audit/` directory untracked)

---

## NEXT ACTION

**Immediate:** Review audit findings with team

**Then:** Begin Tier 1 data collection:
1. Manual download Delhi GTFS (both bus + metro)
2. Identify and collect population data sources
3. Collect Mumbai Suburban service frequency from MRVC
4. Collect Chennai Metro station coordinates from CMRL
5. Identify LGD spatial boundary sources

**Reference:** See `state_coverage_audit_report.md` for complete analysis and `state_mode_remaining_work.csv` for full priority list.

---

**Audit Completion:** ✅ 2026-09-29  
**Auditor:** Automated + Manual Repository Analysis  
**Report Location:** `ml/fields/public_transport/audit/`
