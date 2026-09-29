import pandas as pd
import zipfile
import os
import io
import json
from pathlib import Path
import xml.etree.ElementTree as ET

RAW_DIR = Path("data/raw/metro")
PROCESSED_DIR = Path("ml/fields/public_transport/metro/data/processed")
REPORTS_DIR = Path("ml/fields/public_transport/metro/reports")

def generate_inventory():
    inventory = []
    
    # Hyderabad GTFS
    hyd_zip = RAW_DIR / "hyderabad" / "telangana_opendata_gtfs_hmrl_03_july_2026.zip"
    if hyd_zip.exists():
        with zipfile.ZipFile(hyd_zip, 'r') as z:
            for filename in z.namelist():
                if not filename.endswith(".txt"): continue
                with z.open(filename) as f:
                    try:
                        text = io.TextIOWrapper(f, encoding='utf-8-sig')
                        df = pd.read_csv(text)
                        inventory.append({
                            "dataset_id": f"metro_hyd_hmrl_{filename.split('.')[0]}",
                            "city": "Hyderabad",
                            "operator": "HMRL",
                            "source": "OpenCity",
                            "filename": filename,
                            "file_format": "TXT/CSV",
                            "file_path": str(hyd_zip),
                            "file_size": z.getinfo(filename).file_size,
                            "row_count": len(df),
                            "column_count": len(df.columns),
                            "columns": ", ".join(df.columns.tolist()),
                            "date_range": "2026",
                            "coordinate_available": "stop_lat" in df.columns,
                            "geometry_available": "shape_pt_lat" in df.columns,
                            "primary_key_candidate": "stop_id" if "stop_id" in df.columns else ("trip_id" if "trip_id" in df.columns else ("route_id" if "route_id" in df.columns else "")),
                            "missing_percentage": round(df.isna().mean().mean() * 100, 2) if not df.empty else 0,
                            "duplicate_percentage": round(df.duplicated().mean() * 100, 2) if not df.empty else 0,
                            "notes": f"Part of GTFS. {filename}"
                        })
                    except Exception as e:
                        print(f"Error reading {filename}: {e}")

    # Bengaluru KML
    blr_kml = RAW_DIR / "bengaluru" / "bengaluru_metro_stations.kml"
    if blr_kml.exists():
        size = os.path.getsize(blr_kml)
        tree = ET.parse(blr_kml)
        root = tree.getroot()
        namespace = {'kml': 'http://www.opengis.net/kml/2.2'}
        placemarks = root.findall('.//kml:Placemark', namespace)
        if not placemarks:
            # Try without namespace
            placemarks = root.findall('.//Placemark')
            
        inventory.append({
            "dataset_id": "metro_bengaluru_stations_kml",
            "city": "Bengaluru",
            "operator": "BMRCL",
            "source": "OpenCity",
            "filename": "bengaluru_metro_stations.kml",
            "file_format": "KML",
            "file_path": str(blr_kml),
            "file_size": size,
            "row_count": len(placemarks),
            "column_count": 2, # name, coords
            "columns": "name, coordinates",
            "date_range": "2024",
            "coordinate_available": True,
            "geometry_available": True,
            "primary_key_candidate": "name",
            "missing_percentage": 0,
            "duplicate_percentage": 0,
            "notes": "KML Placemarks"
        })

    # Bengaluru Ridership
    blr_csv = RAW_DIR / "bengaluru" / "bmrcl_station_ridership.csv"
    if blr_csv.exists():
        df = pd.read_csv(blr_csv, on_bad_lines='skip')
        inventory.append({
            "dataset_id": "metro_bengaluru_bmrcl_ridership_csv",
            "city": "Bengaluru",
            "operator": "BMRCL",
            "source": "OpenCity",
            "filename": "bmrcl_station_ridership.csv",
            "file_format": "CSV",
            "file_path": str(blr_csv),
            "file_size": os.path.getsize(blr_csv),
            "row_count": len(df),
            "column_count": len(df.columns),
            "columns": ", ".join(df.columns.tolist()),
            "date_range": "2024",
            "coordinate_available": False,
            "geometry_available": False,
            "primary_key_candidate": "code",
            "missing_percentage": round(df.isna().mean().mean() * 100, 2) if not df.empty else 0,
            "duplicate_percentage": round(df.duplicated().mean() * 100, 2) if not df.empty else 0,
            "notes": "Seems to be just station codes"
        })

    # Chennai Ridership
    chn_csv = RAW_DIR / "chennai" / "cmrl_metro_ridership_2023_26.csv"
    if chn_csv.exists():
        df = pd.read_csv(chn_csv)
        inventory.append({
            "dataset_id": "metro_chennai_cmrl_ridership_csv",
            "city": "Chennai",
            "operator": "CMRL",
            "source": "OpenCity",
            "filename": "cmrl_metro_ridership_2023_26.csv",
            "file_format": "CSV",
            "file_path": str(chn_csv),
            "file_size": os.path.getsize(chn_csv),
            "row_count": len(df),
            "column_count": len(df.columns),
            "columns": ", ".join(df.columns.tolist()),
            "date_range": "2023-2026",
            "coordinate_available": False,
            "geometry_available": False,
            "primary_key_candidate": "Month",
            "missing_percentage": round(df.isna().mean().mean() * 100, 2) if not df.empty else 0,
            "duplicate_percentage": round(df.duplicated().mean() * 100, 2) if not df.empty else 0,
            "notes": "Monthly ridership totals"
        })

    df_inv = pd.DataFrame(inventory)
    df_inv.to_csv(PROCESSED_DIR / "metro_data_inventory.csv", index=False)
    print("Inventory created.")

if __name__ == "__main__":
    generate_inventory()
