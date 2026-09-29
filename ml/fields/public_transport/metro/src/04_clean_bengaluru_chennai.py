"""Clean Bengaluru and Chennai Metro data.

Phases 5-7: Clean Bengaluru KML stations, station list, and Chennai ridership.
"""

from __future__ import annotations

import pandas as pd
import re
from pathlib import Path
from lxml import etree
from datetime import datetime

ROOT = Path(__file__).resolve().parents[5]
RAW_BLR = ROOT / "data" / "raw" / "metro" / "bengaluru"
RAW_CHN = ROOT / "data" / "raw" / "metro" / "chennai"
PROCESSED = ROOT / "ml" / "fields" / "public_transport" / "metro" / "data" / "processed"


def clean_bengaluru_kml() -> pd.DataFrame:
    """Phase 5: Parse and clean Bengaluru Metro stations from KML."""
    
    print("Phase 5: Cleaning Bengaluru KML stations...")
    
    kml_path = RAW_BLR / "bengaluru_metro_stations.kml"
    tree = etree.parse(str(kml_path))
    root = tree.getroot()
    ns = {"kml": "http://www.opengis.net/kml/2.2"}
    
    stations = []
    placemarks = root.findall(".//kml:Placemark", ns)
    
    for pm in placemarks:
        station = {}
        
        # Name
        name_elem = pm.find(".//kml:name", ns)
        if name_elem is not None:
            station['station_name'] = name_elem.text
        
        # Coordinates
        coords_elem = pm.find(".//kml:coordinates", ns)
        if coords_elem is not None:
            coords_text = coords_elem.text.strip()
            parts = coords_text.split(',')
            if len(parts) >= 2:
                station['longitude'] = float(parts[0])
                station['latitude'] = float(parts[1])
        
        # Extended data
        extended = pm.find(".//kml:ExtendedData", ns)
        if extended is not None:
            for data in extended.findall(".//kml:Data", ns):
                name = data.get("name")
                value_elem = data.find(".//kml:value", ns)
                if value_elem is not None and name:
                    station[name] = value_elem.text
        
        if 'station_name' in station and 'latitude' in station:
            stations.append(station)
    
    df = pd.DataFrame(stations)
    
    # Validate coordinates
    df = df[(df['latitude'] >= 12.8) & (df['latitude'] <= 13.2)]
    df = df[(df['longitude'] >= 77.4) & (df['longitude'] <= 77.8)]
    
    # Add city and operator
    df['city'] = 'Bengaluru'
    df['operator'] = 'BMRCL'
    df['source'] = 'OpenCity.in KML'
    
    # Create clean station ID
    df['station_id'] = 'BLR_' + pd.Series(range(1, len(df) + 1)).astype(str).str.zfill(3)
    
    # Reorder columns
    cols = ['station_id', 'station_name', 'latitude', 'longitude', 'city', 'operator', 'source']
    other_cols = [c for c in df.columns if c not in cols]
    df = df[cols + other_cols]
    
    # Save
    output_dir = PROCESSED / "bengaluru"
    output_dir.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_dir / "stations_clean.csv", index=False)
    
    print(f"✓ Cleaned {len(df)} Bengaluru stations")
    return df


def clean_bengaluru_station_list() -> pd.DataFrame:
    """Phase 6: Clean Bengaluru station code list (NO ridership data)."""
    
    print("\nPhase 6: Cleaning Bengaluru station list...")
    
    df = pd.read_csv(RAW_BLR / "bmrcl_station_ridership.csv")
    
    # Remove duplicates
    df = df.drop_duplicates()
    
    # Add metadata
    df['city'] = 'Bengaluru'
    df['operator'] = 'BMRCL'
    df['source'] = 'OpenCity.in station list'
    df.rename(columns={'code': 'station_code', 'name': 'station_name'}, inplace=True)
    
    # Save
    output_dir = PROCESSED / "bengaluru"
    output_dir.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_dir / "station_codes_clean.csv", index=False)
    
    print(f"✓ Cleaned {len(df)} station codes (NO RIDERSHIP DATA in source)")
    return df


def parse_indian_number(s: str) -> int:
    """Parse Indian comma-formatted number: '43,77,813' -> 4377813."""
    if pd.isna(s) or s == '-':
        return None
    return int(str(s).replace(',', ''))


def parse_percentage(s: str) -> float:
    """Parse percentage: '65.15%' -> 65.15."""
    if pd.isna(s) or s == '-':
        return None
    return float(str(s).rstrip('%'))


def clean_chennai_ridership() -> pd.DataFrame:
    """Phase 7: Clean Chennai monthly ridership data."""
    
    print("\nPhase 7: Cleaning Chennai ridership...")
    
    df = pd.read_csv(RAW_CHN / "cmrl_metro_ridership_2023_26.csv", encoding='utf-8-sig')
    
    # Parse month-year
    df['month_str'] = df['Month']
    df['date'] = pd.to_datetime(df['Month'], format='%b-%y', errors='coerce')
    df['year'] = df['date'].dt.year
    df['month'] = df['date'].dt.month
    df['year_month'] = df['date'].dt.strftime('%Y-%m')
    
    # Parse ridership fields (Indian number format)
    df['closed_loop_ridership'] = df['Closed Loop (Ridership)'].apply(parse_indian_number)
    df['qr_ridership'] = df['QR Tickets (Ridership)'].apply(parse_indian_number)
    df['ncmc_ridership'] = df['NCMC (Ridership)'].apply(parse_indian_number)
    df['total_ridership'] = df['Total Passenger Flow'].apply(parse_indian_number)
    
    # Parse percentages
    df['closed_loop_pct'] = df['Closed Loop %'].apply(parse_percentage)
    df['qr_pct'] = df['QR %'].apply(parse_percentage)
    df['ncmc_pct'] = df['NCMC %'].apply(parse_percentage)
    
    # Add metadata
    df['city'] = 'Chennai'
    df['operator'] = 'CMRL'
    df['source'] = 'OpenCity.in monthly ridership'
    
    # Select clean columns
    clean_df = df[[
        'year_month', 'year', 'month', 'month_str',
        'closed_loop_ridership', 'closed_loop_pct',
        'qr_ridership', 'qr_pct',
        'ncmc_ridership', 'ncmc_pct',
        'total_ridership',
        'city', 'operator', 'source'
    ]]
    
    # Sort by date
    clean_df = clean_df.sort_values('year_month')
    
    # Validate
    clean_df['ridership_sum'] = (clean_df['closed_loop_ridership'].fillna(0) + 
                                   clean_df['qr_ridership'].fillna(0) + 
                                   clean_df['ncmc_ridership'].fillna(0))
    clean_df['ridership_diff'] = abs(clean_df['total_ridership'] - clean_df['ridership_sum'])
    
    # Save
    output_dir = PROCESSED / "chennai"
    output_dir.mkdir(parents=True, exist_ok=True)
    clean_df.to_csv(output_dir / "monthly_ridership_clean.csv", index=False)
    
    max_diff = clean_df['ridership_diff'].max()
    print(f"✓ Cleaned {len(clean_df)} months of ridership data")
    print(f"  Date range: {clean_df['year_month'].min()} to {clean_df['year_month'].max()}")
    print(f"  Max component sum difference: {max_diff} passengers")
    
    return clean_df


def main():
    """Run all Bengaluru and Chennai cleaning."""
    
    blr_stations = clean_bengaluru_kml()
    blr_codes = clean_bengaluru_station_list()
    chn_ridership = clean_chennai_ridership()
    
    print("\n" + "="*60)
    print("Phases 5-7 Complete")
    print("="*60)
    print(f"Bengaluru: {len(blr_stations)} stations with coordinates")
    print(f"Bengaluru: {len(blr_codes)} station codes")
    print(f"Chennai: {len(chn_ridership)} months of ridership")
    

if __name__ == "__main__":
    main()
