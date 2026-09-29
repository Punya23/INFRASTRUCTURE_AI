import pandas as pd
import re

def standardize_col_name(col):
    if not isinstance(col, str):
        return str(col)
    col = str(col).lower()
    # Remove parentheses and their contents, or just remove parentheses characters?
    # The prompt says: "no parentheses". Examples: "State Name (In English)" -> "state_name"
    col = re.sub(r'\(.*?\)', '', col)
    # the ward typo: "Distrct Name" -> "district_name"
    col = col.replace("distrct", "district")
    # Replace non-alphanumeric with space
    col = re.sub(r'[^a-z0-9]', ' ', col)
    # Split and join with underscore
    col = '_'.join(col.split())
    # Custom fixes if needed
    col = col.replace("localbody_", "local_body_")
    if col == "s_no":
        col = "s_no"
    return col

def clean_string(val):
    if pd.isna(val):
        return pd.NA
    if isinstance(val, str):
        val = re.sub(r'\s+', ' ', val).strip()
        if val.lower() in ["", "na", "n/a", "null", "none"]:
            return pd.NA
    return val

def clean_dataframe(df):
    # Standardize column names
    cols = [standardize_col_name(c) for c in df.columns]
    
    # Deduplicate column names
    seen = {}
    new_cols = []
    for c in cols:
        if c in seen:
            seen[c] += 1
            new_cols.append(f"{c}_{seen[c]}")
        else:
            seen[c] = 0
            new_cols.append(c)
    df.columns = new_cols
    
    # Remove completely empty rows and columns
    df = df.dropna(how='all', axis=0)
    df = df.dropna(how='all', axis=1)
    
    # Apply string cleaning
    for col in df.columns:
        if df[col].dtype == 'object':
            df[col] = df[col].apply(clean_string)
            
    return df

def find_header_row(df_raw):
    # Iterate over rows to find where there are multiple non-null columns (at least 3)
    for i in range(len(df_raw)):
        row_non_na = df_raw.iloc[i].dropna().shape[0]
        if row_non_na >= 3:
            return i
    return 0

def load_lgd_excel(path):
    df_raw = pd.read_excel(path, header=None)
    header_idx = find_header_row(df_raw)
    
    df = pd.read_excel(path, header=header_idx)
    return clean_dataframe(df)

def safely_convert_to_int(df, columns):
    for col in columns:
        if col in df.columns:
            # We want to keep it nullable integer, but avoid converting things like "01" if it destroys leading zeros?
            # Actually, LGD codes are just integers, they don't have meaningful leading zeros unless they are ward numbers.
            # "Do NOT blindly convert codes to integers if doing so would destroy meaningful leading zeros... Ward numbers may contain '1A'"
            # For codes (state_code, district_code, etc.), Int64 (nullable int) is fine.
            try:
                # pandas Int64Dtype allows NA and integers
                df[col] = pd.to_numeric(df[col], errors='coerce').astype('Int64')
            except Exception:
                pass
    return df
