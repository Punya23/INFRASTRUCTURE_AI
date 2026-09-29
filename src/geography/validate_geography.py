import pandas as pd
from pathlib import Path
import sys

def check_file(path, required_cols):
    if not path.exists():
        print(f"FAIL: File {path} does not exist.")
        return False, None
    df = pd.read_csv(path)
    if df.empty:
        print(f"FAIL: File {path} is empty.")
        return False, df
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        print(f"FAIL: File {path} missing columns: {missing}")
        return False, df
    return True, df

def main():
    proc_dir = Path("data/processed/geography")
    
    success = True
    
    # Check states
    st_ok, df_states = check_file(proc_dir / "states_clean.csv", ["state_code", "state_name"])
    success &= st_ok
    if st_ok:
        if df_states['state_code'].isna().any():
            print("FAIL: states_clean.csv has null state_code.")
            success = False
            
    # Check districts
    dt_ok, df_dist = check_file(proc_dir / "districts_clean.csv", ["state_code", "district_code", "district_name"])
    success &= dt_ok
    if dt_ok:
        if df_dist['district_code'].isna().any():
            print("FAIL: districts_clean.csv has null district_code.")
            success = False
            
    # Check subdistricts
    sdt_ok, df_subdist = check_file(proc_dir / "subdistricts_clean.csv", ["district_code", "subdistrict_code"])
    success &= sdt_ok
    
    # Check ulbs
    ulb_ok, df_ulbs = check_file(proc_dir / "ulbs_clean.csv", ["state_code", "local_body_code"])
    success &= ulb_ok
    if ulb_ok:
        if df_ulbs['local_body_code'].isna().any():
            print("FAIL: ulbs_clean.csv has null local_body_code.")
            success = False
            
    # Check wards
    wd_ok, df_wards = check_file(proc_dir / "wards_all_available_clean.csv", ["local_body_code", "ward_code", "ward_number", "ward_source_state"])
    success &= wd_ok
    
    # Relationships
    if st_ok and dt_ok:
        st_codes = set(df_states['state_code'].dropna())
        dt_st_codes = set(df_dist['state_code'].dropna())
        unmatched = dt_st_codes - st_codes
        if unmatched:
            print(f"FAIL: Districts have state_codes not in states_clean.csv: {unmatched}")
            success = False
            
    if ulb_ok and wd_ok:
        ulb_codes = set(df_ulbs['local_body_code'].dropna())
        wd_ulb_codes = set(df_wards['local_body_code'].dropna())
        # Ward coverage is limited, but whatever local_body_code is in wards SHOULD ideally be in ulbs, or at least we check
        unmatched = wd_ulb_codes - ulb_codes
        if unmatched:
            print(f"WARNING: Wards have local_body_codes not in ulbs_clean.csv: {len(unmatched)} codes.")
            # Not failing the whole script on this because source data might have mismatches, but logging a warning.
            
    if success:
        print("SUCCESS: Geography pipeline validation passed.")
        sys.exit(0)
    else:
        print("Validation failed.")
        sys.exit(1)

if __name__ == "__main__":
    main()
