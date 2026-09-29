import pandas as pd
from pathlib import Path
from utils import load_lgd_excel, safely_convert_to_int

def main():
    raw_dir = Path("data/raw/geography/ulbs")
    proc_dir = Path("data/processed/geography")
    
    files = list(raw_dir.glob("*.xlsx"))
    if not files:
        print("No ulbs raw file found.")
        return
        
    df = load_lgd_excel(files[0])
    
    if "s_no" in df.columns:
        df = df.drop(columns=["s_no"])
        
    df = df.rename(columns={"local_body_name_1": "local_body_name_local"})
        
    cols_to_int = ["state_code", "local_body_code", "local_body_version", "localbody_type_code", "census_2011_code"]
    df = safely_convert_to_int(df, cols_to_int)
    
    df.to_csv(proc_dir / "ulbs_clean.csv", index=False)
    print("Cleaned ulbs saved to ulbs_clean.csv")

if __name__ == "__main__":
    main()
