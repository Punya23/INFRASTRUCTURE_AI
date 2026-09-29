"""Generate comprehensive Metro data inventory.

Inspects all raw Metro files and creates detailed inventory with file metadata,
row counts, column information, and quality indicators.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
from lxml import etree

ROOT = Path(__file__).resolve().parents[5]
RAW_METRO = ROOT / "data" / "raw" / "metro"
PROCESSED = ROOT / "ml" / "fields" / "public_transport" / "metro" / "data" / "processed"


def get_file_size(path: Path) -> int:
    """Get file size in bytes."""
    return path.stat().st_size


def inspect_csv(path: Path) -> dict[str, Any]:
    """Inspect a CSV file."""
    try:
        df = pd.read_csv(path)
        return {
            "row_count": len(df),
            "column_count": len(df.columns),
            "columns": ", ".join(df.columns),
            "missing_pct": round(df.isnull().sum().sum() / (len(df) * len(df.columns)) * 100, 2),
            "duplicate_pct": round((df.duplicated().sum() / len(df)) * 100, 2) if len(df) > 0 else 0,
        }
    except (OSError, ValueError) as e:  # pandas parse errors subclass ValueError
        # Try with error_bad_lines=False or inspect manually
        try:
            with open(path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            # Count columns from header
            header = lines[0].strip().split(',')
            return {
                "row_count": len(lines) - 1,
                "column_count": len(header),
                "columns": ", ".join(header),
                "missing_pct": 0,
                "duplicate_pct": 0,
            }
        except (OSError, ValueError, IndexError):  # unreadable, undecodable or empty file
            return {
                "row_count": 0,
                "column_count": 0,
                "columns": f"ERROR: {e!s}",
                "missing_pct": 0,
                "duplicate_pct": 0,
            }


def inspect_kml(path: Path) -> dict[str, Any]:
    """Inspect a KML file."""
    tree = etree.parse(str(path))
    root = tree.getroot()
    ns = {"kml": "http://www.opengis.net/kml/2.2"}
    placemarks = root.findall(".//kml:Placemark", ns)
    
    # Extract field names from first placemark
    columns = set()
    if placemarks:
        extended_data = placemarks[0].find(".//kml:ExtendedData", ns)
        if extended_data is not None:
            for data in extended_data.findall(".//kml:Data", ns):
                name = data.get("name")
                if name:
                    columns.add(name)
    
    return {
        "row_count": len(placemarks),
        "column_count": len(columns) + 2,  # +2 for name and coordinates
        "columns": "name, coordinates, " + ", ".join(sorted(columns)),
        "missing_pct": 0,  # Would require detailed inspection
        "duplicate_pct": 0,  # Would require detailed inspection
    }


def create_inventory() -> None:
    """Create comprehensive Metro data inventory."""
    inventory = []
    
    # Hyderabad GTFS files
    hyd_dir = RAW_METRO / "hyderabad"
    gtfs_files = [
        "agency.txt", "stops.txt", "routes.txt", "trips.txt", 
        "stop_times.txt", "calendar.txt", "shapes.txt",
        "fare_attributes.txt", "fare_rules.txt", "feed_info.txt"
    ]
    
    for filename in gtfs_files:
        filepath = hyd_dir / filename
        if filepath.exists():
            stats = inspect_csv(filepath)
            inventory.append({
                "dataset_id": f"hyderabad_gtfs_{filename.replace('.txt', '')}",
                "city": "Hyderabad",
                "operator": "HMRL",
                "source": "OpenCity.in via Telangana Open Data",
                "filename": filename,
                "file_format": "CSV (GTFS)",
                "file_path": str(filepath.relative_to(ROOT)),
                "file_size": get_file_size(filepath),
                **stats,
                "date_range": "2026-07-03 to 2030-01-01 (from feed_info)" if filename == "feed_info.txt" else "N/A",
                "coordinate_available": "Yes" if filename == "stops.txt" else "No",
                "geometry_available": "Yes (LineString)" if filename == "shapes.txt" else "No",
                "primary_key_candidate": {
                    "agency.txt": "agency_id",
                    "stops.txt": "stop_id",
                    "routes.txt": "route_id",
                    "trips.txt": "trip_id",
                    "stop_times.txt": "(trip_id, stop_sequence)",
                    "calendar.txt": "service_id",
                    "shapes.txt": "(shape_id, shape_pt_sequence)",
                    "fare_attributes.txt": "fare_id",
                    "fare_rules.txt": "(origin_id, destination_id)",
                    "feed_info.txt": "N/A"
                }.get(filename, "N/A"),
                "notes": f"GTFS {filename.replace('.txt', '')} component"
            })
    
    # Bengaluru KML stations
    blr_kml = RAW_METRO / "bengaluru" / "bengaluru_metro_stations.kml"
    if blr_kml.exists():
        stats = inspect_kml(blr_kml)
        inventory.append({
            "dataset_id": "bengaluru_metro_stations_kml",
            "city": "Bengaluru",
            "operator": "BMRCL",
            "source": "OpenCity.in",
            "filename": "bengaluru_metro_stations.kml",
            "file_format": "KML",
            "file_path": str(blr_kml.relative_to(ROOT)),
            "file_size": get_file_size(blr_kml),
            **stats,
            "date_range": "N/A",
            "coordinate_available": "Yes",
            "geometry_available": "Yes (Point)",
            "primary_key_candidate": "@id",
            "notes": "Station locations with names and colors"
        })
    
    # Bengaluru ridership
    blr_ridership = RAW_METRO / "bengaluru" / "bmrcl_station_ridership.csv"
    if blr_ridership.exists():
        stats = inspect_csv(blr_ridership)
        inventory.append({
            "dataset_id": "bengaluru_metro_ridership",
            "city": "Bengaluru",
            "operator": "BMRCL",
            "source": "OpenCity.in",
            "filename": "bmrcl_station_ridership.csv",
            "file_format": "CSV",
            "file_path": str(blr_ridership.relative_to(ROOT)),
            "file_size": get_file_size(blr_ridership),
            **stats,
            "date_range": "N/A (no temporal data)",
            "coordinate_available": "No",
            "geometry_available": "No",
            "primary_key_candidate": "code",
            "notes": "Station codes and names only; NO RIDERSHIP VALUES despite filename"
        })
    
    # Chennai ridership
    chennai_ridership = RAW_METRO / "chennai" / "cmrl_metro_ridership_2023_26.csv"
    if chennai_ridership.exists():
        stats = inspect_csv(chennai_ridership)
        inventory.append({
            "dataset_id": "chennai_metro_ridership",
            "city": "Chennai",
            "operator": "CMRL",
            "source": "OpenCity.in",
            "filename": "cmrl_metro_ridership_2023_26.csv",
            "file_format": "CSV",
            "file_path": str(chennai_ridership.relative_to(ROOT)),
            "file_size": get_file_size(chennai_ridership),
            **stats,
            "date_range": "Apr-23 to Jun-26",
            "coordinate_available": "No",
            "geometry_available": "No",
            "primary_key_candidate": "Month",
            "notes": "Monthly system-wide ridership by ticket type (Closed Loop, QR, NCMC)"
        })
    
    # Write inventory
    PROCESSED.mkdir(parents=True, exist_ok=True)
    output_path = PROCESSED / "metro_data_inventory.csv"
    
    df_inventory = pd.DataFrame(inventory)
    df_inventory.to_csv(output_path, index=False)
    
    print(f"✓ Metro data inventory created: {output_path.relative_to(ROOT)}")
    print(f"  Total datasets: {len(inventory)}")
    print(f"  Cities: {', '.join(sorted(df_inventory['city'].unique()))}")
    print("\nDataset summary:")
    for _, row in df_inventory.iterrows():
        print(f"  {row['dataset_id']}: {row['row_count']} rows, {row['column_count']} columns")


if __name__ == "__main__":
    create_inventory()
