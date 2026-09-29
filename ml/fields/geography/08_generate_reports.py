from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


def main():
    proc_dir = Path("ml/fields/geography/data/processed")
    reports_dir = Path("ml/fields/geography/reports")
    fig_dir = reports_dir / "figures"
    fig_dir.mkdir(parents=True, exist_ok=True)
    
    # Load processed data
    districts = pd.read_csv(proc_dir / "districts_clean.csv")
    ulbs = pd.read_csv(proc_dir / "ulbs_clean.csv")
    wards = pd.read_csv(proc_dir / "wards_all_available_clean.csv")
    missing_data = pd.read_csv(reports_dir / "step0_missing_values.csv")
    
    # 1. District count by state
    dist_counts = districts.groupby('state_name')['district_code'].nunique().sort_values(ascending=False).head(20)
    plt.figure(figsize=(10, 6))
    dist_counts.plot(kind='bar')
    plt.title("Top 20 States by District Count")
    plt.xlabel("State Name")
    plt.ylabel("District Count")
    plt.tight_layout()
    plt.savefig(fig_dir / "district_count_by_state.png")
    plt.close()
    
    # 2. ULB count by state
    ulb_counts = ulbs.groupby('state_name')['local_body_code'].nunique().sort_values(ascending=False).head(20)
    plt.figure(figsize=(10, 6))
    ulb_counts.plot(kind='bar')
    plt.title("Top 20 States by ULB Count")
    plt.xlabel("State Name")
    plt.ylabel("ULB Count")
    plt.tight_layout()
    plt.savefig(fig_dir / "ulb_count_by_state.png")
    plt.close()
    
    # 3. Ward count by available state
    ward_counts = wards.groupby('ward_source_state')['ward_code'].nunique().sort_values(ascending=False)
    plt.figure(figsize=(8, 5))
    ward_counts.plot(kind='bar')
    plt.title("Ward Count by Available State")
    plt.xlabel("State")
    plt.ylabel("Ward Count")
    plt.tight_layout()
    plt.savefig(fig_dir / "ward_count_by_state.png")
    plt.close()
    
    # 4. Ward count distribution per ULB
    ward_per_ulb = wards.groupby('local_body_code')['ward_code'].nunique()
    plt.figure(figsize=(8, 5))
    plt.hist(ward_per_ulb, bins=30, edgecolor='black')
    plt.title("Distribution of Wards per ULB")
    plt.xlabel("Number of Wards")
    plt.ylabel("Number of ULBs")
    plt.tight_layout()
    plt.savefig(fig_dir / "ward_distribution_per_ulb.png")
    plt.close()
    
    # 5. Missing-value percentage chart
    # Top 15 columns with highest missing percentage
    top_missing = missing_data.sort_values('Missing %', ascending=False).head(15)
    plt.figure(figsize=(10, 6))
    plt.barh(top_missing['Dataset'] + " - " + top_missing['Column'], top_missing['Missing %'])
    plt.title("Top 15 Columns with Highest Missing Values %")
    plt.xlabel("Missing Percentage (%)")
    plt.gca().invert_yaxis()
    plt.tight_layout()
    plt.savefig(fig_dir / "missing_value_percentages.png")
    plt.close()
    
    print("Charts generated in reports/figures/")

if __name__ == "__main__":
    main()
