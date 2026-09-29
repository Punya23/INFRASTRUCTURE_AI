import os
import shutil
import pandas as pd
from pathlib import Path

def get_state_from_title(title_str):
    if not isinstance(title_str, str):
        return None
    title_str = title_str.lower()
    if 'maharashtra' in title_str:
        return 'maharashtra'
    elif 'karnataka' in title_str:
        return 'karnataka'
    elif 'tamil nadu' in title_str:
        return 'tamil_nadu'
    elif 'delhi' in title_str:
        return 'delhi'
    return None

def main():
    source_dir = Path("public-transport")
    raw_dir = Path("data/raw/geography")
    reports_dir = Path("reports")
    
    files = list(source_dir.glob("*.xlsx"))
    
    inventory = []
    
    for f in files:
        fname = f.name
        fsize = f.stat().st_size
        
        # Determine target directory
        if fname.startswith("All_Stateof_India"):
            target_sub = "states"
            category = "States"
        elif fname.startswith("All_Districtof_India"):
            target_sub = "districts"
            category = "Districts"
        elif fname.startswith("All_Sub_Districtof_India"):
            target_sub = "subdistricts"
            category = "Subdistricts"
        elif fname.startswith("Urban_Local_Body_India"):
            target_sub = "ulbs"
            category = "ULBs"
        elif fname.startswith("Statewise_localbody_ward_coverage"):
            target_sub = "wards"
            category = "Wards"
        elif fname.startswith("Statewise_ulbs_coverage"):
            target_sub = "ulb_coverage_extra"
            category = "ULB Coverage"
        else:
            target_sub = "other"
            category = "Other"
            
        # Inspect excel
        try:
            xl = pd.ExcelFile(f)
            sheet_names = xl.sheet_names
            
            # Read first few rows to get title and actual header
            df_sample = pd.read_excel(f, nrows=10, header=None)
            rows, cols = 0, 0
            
            # Count actual rows
            df_full = pd.read_excel(f, header=None)
            rows, cols = df_full.shape
            
            # Determine state for wards
            target_dir = raw_dir / target_sub
            
            title_val = str(df_sample.iloc[0, 0]) if not df_sample.empty else ""
            
            if target_sub == "wards":
                state = get_state_from_title(title_val)
                if state:
                    target_dir = raw_dir / "wards" / state
                else:
                    target_dir = raw_dir / "wards" / "unknown"
            
            # Ensure target_dir exists
            target_dir.mkdir(parents=True, exist_ok=True)
            
            # Copy file
            target_path = target_dir / fname
            if not target_path.exists():
                shutil.copy2(f, target_path)
            
            inv_record = {
                "Filename": fname,
                "Category": category,
                "File Size (Bytes)": fsize,
                "Sheet Names": ", ".join(sheet_names),
                "Rows": rows,
                "Columns": cols,
                "Target Path": str(target_path)
            }
            inventory.append(inv_record)
            
            print(f"Processed {fname} -> {target_path}")
            
        except Exception as e:
            print(f"Error processing {fname}: {e}")
            
    df_inv = pd.DataFrame(inventory)
    df_inv.to_csv(reports_dir / "step0_file_inventory.csv", index=False)
    
    with open(reports_dir / "step0_file_inventory.md", "w") as md_file:
        md_file.write("# Step 0: File Inventory\n\n")
        md_file.write(df_inv.to_markdown(index=False))
        
if __name__ == "__main__":
    main()
