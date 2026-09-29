import pandas as pd
from pathlib import Path
from utils import load_lgd_excel, safely_convert_to_int

def main():
    raw_dir = Path("data/raw/geography/states")
    proc_dir = Path("data/processed/geography")
    
    files = list(raw_dir.glob("*.xlsx"))
    if not files:
        print("No states raw file found.")
        return
        
    df = load_lgd_excel(files[0])
    
    if "s_no" in df.columns:
        df = df.drop(columns=["s_no"])
        
    df = df.rename(columns={"state_name_1": "state_name_local"})
        
    cols_to_int = ["state_code", "state_version", "census_2001_code", "census_2011_code"]
    df = safely_convert_to_int(df, cols_to_int)
    
    df.to_csv(proc_dir / "states_clean.csv", index=False)
    print("Cleaned states saved to states_clean.csv")

if __name__ == "__main__":
    main()
