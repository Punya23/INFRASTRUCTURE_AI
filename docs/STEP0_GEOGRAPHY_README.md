# STEP 0: Geography Pipeline

## Purpose
Build a clean, reproducible, India-wide geographic foundation for the LokDrishti AI Public Transport system using official LGD (Local Government Directory) datasets.

## Source
Government of India Local Government Directory (LGD). Raw files are Excel exports representing states, districts, subdistricts, ULBs, and wards.

## Folder Structure
- `ml/fields/geography/data/raw/`: Original downloaded Excel files.
- `ml/fields/geography/data/processed/`: Cleaned, standardized CSV outputs.
- `ml/fields/geography/`: Python scripts for data loading, cleaning, validation, and reporting.
- `ml/fields/geography/reports/`: Data quality, missing values, duplicates, coverage reports, and charts.
- `ml/fields/geography/notebooks/`: EDA notebooks for geography analysis.

## Cleaning Process
- Standardized all column names (snake_case, lowercased, removed parentheses).
- Formatted missing values (NA, None, null, empty spaces -> actual nulls).
- Validated codes natively (integer/Int64 for safe numerical conversion without losing strings for things like `ward_number`).
- Handled dataset-specific inconsistencies and headers reliably.

## Validation
- Ensured required columns and geographic codes exist without unexpected nulls.
- Matched relational codes across hierarchy layers where feasible (e.g. ward `local_body_code` against `ulbs` table).
- Tracked duplication limits for composite keys (`local_body_code`, `ward_code`).
- Run `python src/geography/validate_geography.py` to assert pipeline integrity.

## Ward Coverage Limitation
Currently, Ward datasets are state-specific and strictly limited to:
- Maharashtra
- Karnataka
- Tamil Nadu
- Delhi
Wards do not represent India-wide coverage. Missing districts, subdistricts or village mappings in the ward datasets reflect actual gaps in LGD data and are not imputed or manufactured.

## How to Rerun
Execute the following sequentially from the root project directory:
```bash
python ml/fields/geography/01_load_raw.py
python ml/fields/geography/02_clean_states.py
python ml/fields/geography/03_clean_districts.py
python ml/fields/geography/04_clean_subdistricts.py
python ml/fields/geography/05_clean_ulbs.py
python ml/fields/geography/06_clean_wards.py
python ml/fields/geography/07_validate_relationships.py
python ml/fields/geography/08_generate_reports.py
python ml/fields/geography/validate_geography.py
```

## Outputs
- Cleaned geographies: `states_clean.csv`, `districts_clean.csv`, `subdistricts_clean.csv`, `ulbs_clean.csv`, `wards_all_available_clean.csv`.
- Relational mapping file: `geography_relationships.csv`.
- Comprehensive reporting on Missing values, Duplicates, and Validation states.
