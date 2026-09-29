import pandas as pd
from pathlib import Path
from utils import load_lgd_excel, safely_convert_to_int

def main():
    raw_dir = Path("ml/fields/geography/data/raw/districts")
    proc_dir = Path("ml/fields/geography/data/processed")
    
    files = list(raw_dir.glob("*.xlsx"))
    if not files:
        print("No districts raw file found.")
        return
        
    df = load_lgd_excel(files[0])
    
    if "s_no" in df.columns:
        df = df.drop(columns=["s_no"])
        
    cols_to_int = ["state_code", "district_code", "census_2001_code", "census_2011_code"]
    df = safely_convert_to_int(df, cols_to_int)
    
    df.to_csv(proc_dir / "districts_clean.csv", index=False)
    print("Cleaned districts saved to districts_clean.csv")

if __name__ == "__main__":
    main()
