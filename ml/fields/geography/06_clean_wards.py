from pathlib import Path

import pandas as pd
from utils import load_lgd_excel, safely_convert_to_int


def main():
    raw_wards_dir = Path("ml/fields/geography/data/raw/wards")
    proc_dir = Path("ml/fields/geography/data/processed")
    
    states = ["maharashtra", "karnataka", "tamil_nadu", "delhi"]
    all_wards = []
    
    for state in states:
        state_dir = raw_wards_dir / state
        files = list(state_dir.glob("*.xlsx"))
        if not files:
            print(f"No wards raw file found for {state}.")
            continue
            
        df = load_lgd_excel(files[0])
        
        # Add source state
        df["ward_source_state"] = state
        
        # Clean specific to wards
        cols_to_int = [
            "local_body_code", "ward_code", "district_code", "district_census_code", 
            "subdistrict_code", "subdistrict_census_code", "village_code", "village_census_code"
        ]
        # Notice that ward_number is NOT in cols_to_int because it can be "1A"
        df = safely_convert_to_int(df, cols_to_int)
        
        if "s_no" in df.columns:
            df = df.drop(columns=["s_no"])
            
        # Ensure column ordering/naming matches expectations
        # Expected: local_body_code, ward_code, local_body_name, ward_number, ward_name, etc.
        df.to_csv(proc_dir / f"wards_{state}_clean.csv", index=False)
        print(f"Cleaned wards for {state} saved.")
        all_wards.append(df)
        
    if all_wards:
        df_all = pd.concat(all_wards, ignore_index=True)
        df_all.to_csv(proc_dir / "wards_all_available_clean.csv", index=False)
        print("Combined wards saved to wards_all_available_clean.csv")

if __name__ == "__main__":
    main()
