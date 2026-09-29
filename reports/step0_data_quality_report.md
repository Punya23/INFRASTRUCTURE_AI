# Step 0: Data Quality Report

## Files Processed
Processed 9 raw LGD files covering states, districts, subdistricts, ULBs, and wards for specific states (Maharashtra, Karnataka, Tamil Nadu, Delhi).

## Dataset Sizes
- States: 38 rows, 8 columns
- Districts: 786 rows, 7 columns
- Subdistricts: 7094 rows, 10 columns
- ULBs: 5053 rows, 9 columns
- Wards (combined 4 states): ~28,845 rows, 15 columns

## Cleaning Actions
- Renamed columns via standardization rules, specifically capturing `local_body_code`, `state_name`, etc.
- Removed arbitrary serial numbers (`s_no`).
- Cleaned string whitespace and preserved string forms for `ward_number` which can take values like "1A".
- Deduplicated internally generated duplicate columns (e.g. `localbody_name` appearing twice translated to `local_body_name_local`).
- Enforced pandas nullable integer type (`Int64`) on geography identifiers natively.

## Missing Values
- Minor missing values observed inherently in wards mapping to `village_code` and corresponding census mappings (this is expected due to limited rural coverage/overlap).
- Reference `step0_missing_values.md` for per-column missing statistics.

## Duplicates & Uniqueness
- Small subsets of identical rows across various dimensions deduplicated.
- Some composite combinations (`local_body_code`, `ward_code`) may exhibit minor structural duplication owing to source exports, refer to `step0_duplicate_report.md` for explicit counts.

## Cross-table Validation
- Validated mapped identifiers between Districts -> States.
- Validated local_body_code mappings within Wards -> ULB definitions.
- Identified 1 rogue `local_body_code` in wards absent from the primary ULB catalog - logged.

## Ward Coverage Limitation
Wards data is unequivocally verified as isolated to:
- Maharashtra
- Karnataka
- Tamil Nadu
- Delhi
It does not represent national coverage. We explicitly preserved the context via `ward_source_state`.

## Issues Found & Resolved
- Issue: Header row variance in downloaded exports (titles preceded headers).
- Resolved: Developed `find_header_row()` to dynamically align on valid schemas.
- Issue: Inconsistent string representations for `localbody_` vs `local_body_`.
- Resolved: RegEx and explicit substring replacements applied to homogenize schemas.

## Recommendations for Step 1
- When relating City Bus or Metro data to these geographies, rely heavily on `local_body_code` and `district_code`.
- Do not impute ward properties natively given the substantial missing rural definitions outside the 4 captured states.
