import pandas as pd
from pathlib import Path
from utils import load_lgd_excel, safely_convert_to_int

def main():
    raw_dir = Path("data/raw/geography/subdistricts")
    proc_dir = Path("data/processed/geography")
    
    files = list(raw_dir.glob("*.xlsx"))
    if not files:
        print("No subdistricts raw file found.")
        return
        
    df = load_lgd_excel(files[0])
    
    if "s_no" in df.columns:
        df = df.drop(columns=["s_no"])
        
    cols_to_int = ["state_code", "district_code", "subdistrict_code", "subdistrict_version", "census_2001_code", "census_2011_code"]
    df = safely_convert_to_int(df, cols_to_int)
    
    df.to_csv(proc_dir / "subdistricts_clean.csv", index=False)
    print("Cleaned subdistricts saved to subdistricts_clean.csv")

if __name__ == "__main__":
    main()
