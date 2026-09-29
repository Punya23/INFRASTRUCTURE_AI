import pandas as pd
from pathlib import Path

def main():
    proc_dir = Path("data/processed/geography")
    reports_dir = Path("reports")
    
    # Load processed data
    states = pd.read_csv(proc_dir / "states_clean.csv")
    districts = pd.read_csv(proc_dir / "districts_clean.csv")
    subdistricts = pd.read_csv(proc_dir / "subdistricts_clean.csv")
    ulbs = pd.read_csv(proc_dir / "ulbs_clean.csv")
    wards = pd.read_csv(proc_dir / "wards_all_available_clean.csv")
    
    # 1. Missing Values Report
    missing_data = []
    for name, df in zip(["States", "Districts", "Subdistricts", "ULBs", "Wards"], [states, districts, subdistricts, ulbs, wards]):
        for col in df.columns:
            missing = df[col].isna().sum()
            total = len(df)
            missing_data.append({
                "Dataset": name,
                "Column": col,
                "Total Rows": total,
                "Missing Count": missing,
                "Missing %": round((missing / total) * 100, 2) if total > 0 else 0
            })
    df_missing = pd.DataFrame(missing_data)
    df_missing.to_csv(reports_dir / "step0_missing_values.csv", index=False)
    with open(reports_dir / "step0_missing_values.md", "w") as f:
        f.write("# Step 0: Missing Values Report\n\n")
        f.write(df_missing.to_markdown(index=False))
        
    # 2. Duplicate Report
    with open(reports_dir / "step0_duplicate_report.md", "w") as f:
        f.write("# Step 0: Duplicate Report\n\n")
        
        for name, df, key in [
            ("States", states, ["state_code"]),
            ("Districts", districts, ["district_code"]),
            ("Subdistricts", subdistricts, ["subdistrict_code"]),
            ("ULBs", ulbs, ["local_body_code"]),
            ("Wards (ward_code)", wards, ["ward_code"]),
            ("Wards (local_body_code, ward_code)", wards, ["local_body_code", "ward_code"])
        ]:
            if not df.empty and all(k in df.columns for k in key):
                dups = df[df.duplicated(subset=key, keep=False)]
                f.write(f"## {name}\n")
                f.write(f"- Exact duplicate rows (all columns): {df.duplicated().sum()}\n")
                f.write(f"- Duplicate keys {key}: {dups.shape[0]} rows affected.\n\n")
                if not dups.empty:
                    f.write("Example duplicates:\n")
                    f.write(dups.head().to_markdown(index=False) + "\n\n")

    # 3. Validation: Ward -> ULB mapping
    ward_ulb_codes = wards['local_body_code'].dropna().unique()
    ulb_codes = ulbs['local_body_code'].dropna().unique()
    matched = set(ward_ulb_codes).intersection(set(ulb_codes))
    unmatched = set(ward_ulb_codes) - set(ulb_codes)
    
    val_data = pd.DataFrame({
        "local_body_code": list(unmatched),
        "status": "unmatched"
    })
    val_data.to_csv(reports_dir / "step0_ward_ulb_validation.csv", index=False)
    
    # 4. State Coverage Analysis
    coverage = []
    coverage.append({"Metric": "Total States in states dataset", "Count": states['state_code'].nunique()})
    for st_code in states['state_code'].unique():
        dist_count = districts[districts['state_code'] == st_code]['district_code'].nunique()
        subdist_count = subdistricts[subdistricts['state_code'] == st_code]['subdistrict_code'].nunique()
        ulb_count = ulbs[ulbs['state_code'] == st_code]['local_body_code'].nunique()
        
        st_name = states[states['state_code'] == st_code]['state_name'].iloc[0] if not states[states['state_code'] == st_code].empty else str(st_code)
        
        coverage.append({"Metric": f"Districts in {st_name}", "Count": dist_count})
        coverage.append({"Metric": f"Subdistricts in {st_name}", "Count": subdist_count})
        coverage.append({"Metric": f"ULBs in {st_name}", "Count": ulb_count})
        
    for w_state in wards['ward_source_state'].unique():
        w_count = wards[wards['ward_source_state'] == w_state]['ward_code'].nunique()
        coverage.append({"Metric": f"Wards available in {w_state}", "Count": w_count})
        
    pd.DataFrame(coverage).to_csv(reports_dir / "step0_geography_coverage.csv", index=False)
    
    # 5. Final Geography Master Relationship (just the relationships)
    # districts -> states
    rel = districts[['state_code', 'district_code']].drop_duplicates().copy()
    
    # subdistricts -> districts -> states
    sub_rel = subdistricts[['state_code', 'district_code', 'subdistrict_code']].drop_duplicates()
    rel = pd.merge(rel, sub_rel, on=['state_code', 'district_code'], how='outer')
    
    # ulbs -> states
    ulb_rel = ulbs[['state_code', 'local_body_code']].drop_duplicates()
    rel = pd.merge(rel, ulb_rel, on=['state_code'], how='outer')
    
    rel.to_csv(proc_dir / "geography_relationships.csv", index=False)
    print("Validation and Relationship reports generated.")

if __name__ == "__main__":
    main()
