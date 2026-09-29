#!/usr/bin/env python3
"""
LOCAL RAIL M2 — Deep EDA + Network Analysis + Infrastructure Features

This script performs:
1. Coordinate quality investigation
2. Deep station EDA
3. Rail line/network EDA
4. Network topology analysis
5. Station spacing analysis
6. Infrastructure feature engineering
7. Missing data matrix documentation

Data integrity: NO fabrication, fail closed, provenance maintained.
"""


# Paths (absolute from script location)
from pathlib import Path

import geopandas as gpd
import pandas as pd
from shapely.geometry import Point

REPO_ROOT = Path(__file__).resolve().parents[5]  # Navigate up to repo root
BASE_DIR = REPO_ROOT / "ml/fields/public_transport/local_rail"
DATA_DIR = BASE_DIR / "data/processed"
REPORTS_DIR = BASE_DIR / "reports"
EDA_DIR = DATA_DIR / "eda"
FEATURES_DIR = DATA_DIR / "features"

# Create directories
EDA_DIR.mkdir(parents=True, exist_ok=True)
FEATURES_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

# Mumbai geographic bounds (reasonable Greater Mumbai + suburbs)
# Extended to include Kalyan, Karjat, Virar corridors
MUMBAI_BOUNDS = {
    'lat_min': 18.75,  # Khopoli area (south)
    'lat_max': 19.55,  # Virar/Vaitarna area (north)
    'lon_min': 72.77,  # Arabian Sea coast
    'lon_max': 73.35   # Karjat/Khopoli area (east)
}


def investigate_coordinate_quality() -> pd.DataFrame:
    """
    Phase 1: Deep coordinate quality investigation.
    
    Investigates why M1 flagged 34 coordinates, classifies issues,
    and determines if corrections are warranted.
    
    IMPORTANT: Does NOT automatically correct coordinates.
    Only corrects if source provides clear evidence.
    """
    print("=" * 60)
    print("PHASE 1: COORDINATE QUALITY INVESTIGATION")
    print("=" * 60)
    
    # Load stations
    stations_df = pd.read_csv(DATA_DIR / "mumbai/mumbai_stations_clean.csv")
    validation_df = pd.read_csv(REPORTS_DIR / "mumbai_coordinate_validation.csv")
    
    # Merge validation results
    stations_df = stations_df.merge(
        validation_df[['station_id', 'valid', 'issue']],
        on='station_id',
        how='left'
    )
    
    investigation = []
    
    for _, row in stations_df.iterrows():
        lat, lon = row['latitude'], row['longitude']
        
        # Classify issue type
        if pd.isna(lat) or pd.isna(lon):
            issue_type = "MISSING_COORDINATE"
            investigation_result = "Coordinate missing in source KML"
            corrected = False
            correction_reason = None
            confidence = "HIGH"
            
        elif row['valid']:
            issue_type = "VALID"
            investigation_result = "Within Mumbai suburban rail service area"
            corrected = False
            correction_reason = None
            confidence = "HIGH"
            
        else:
            # Flagged coordinate — investigate why
            lat_valid = MUMBAI_BOUNDS['lat_min'] <= lat <= MUMBAI_BOUNDS['lat_max']
            lon_valid = MUMBAI_BOUNDS['lon_min'] <= lon <= MUMBAI_BOUNDS['lon_max']
            
            if not lat_valid and not lon_valid:
                # Check if lat/lon swapped
                if (MUMBAI_BOUNDS['lat_min'] <= lon <= MUMBAI_BOUNDS['lat_max'] and 
                    MUMBAI_BOUNDS['lon_min'] <= lat <= MUMBAI_BOUNDS['lon_max']):
                    issue_type = "POSSIBLE_LAT_LON_SWAP"
                    investigation_result = "Lat/lon possibly swapped (within bounds if reversed)"
                    corrected = False  # Do NOT auto-correct
                    correction_reason = "Source order unclear, manual review needed"
                    confidence = "LOW"
                else:
                    issue_type = "OUT_OF_RANGE"
                    investigation_result = f"Outside Greater Mumbai bounds (lat={lat:.4f}, lon={lon:.4f})"
                    corrected = False
                    correction_reason = None
                    confidence = "HIGH"
                    
            elif not lat_valid:
                issue_type = "SUSPICIOUS_LATITUDE"
                investigation_result = f"Latitude {lat:.4f} outside Mumbai range [{MUMBAI_BOUNDS['lat_min']}, {MUMBAI_BOUNDS['lat_max']}]"
                corrected = False
                correction_reason = None
                confidence = "HIGH"
                
            elif not lon_valid:
                # Many stations are legitimately outside narrow Mumbai bounds
                # (Kalyan, Karjat, Khopoli are valid suburban rail terminals)
                if lon > MUMBAI_BOUNDS['lon_max']:
                    issue_type = "VALID_EASTERN_SUBURB"
                    investigation_result = f"Legitimate eastern suburb station (lon={lon:.4f})"
                    corrected = False
                    correction_reason = "Station is valid Mumbai Suburban Railway terminus (Central line)"
                    confidence = "HIGH"
                else:
                    issue_type = "SUSPICIOUS_LONGITUDE"
                    investigation_result = f"Longitude {lon:.4f} outside Mumbai range"
                    corrected = False
                    correction_reason = None
                    confidence = "MEDIUM"
        
        investigation.append({
            'station_id': row['station_id'],
            'station_name': row['station_name'],
            'original_latitude': lat,
            'original_longitude': lon,
            'issue_type': issue_type,
            'investigation_result': investigation_result,
            'corrected': corrected,
            'correction_reason': correction_reason if correction_reason else "",
            'source': row['source'],
            'confidence': confidence
        })
    
    investigation_df = pd.DataFrame(investigation)
    
    # Save investigation report
    investigation_df.to_csv(REPORTS_DIR / "mumbai_coordinate_investigation.csv", index=False)
    
    print(f"✓ Investigated {len(investigation_df)} stations")
    print(f"  - Valid: {(investigation_df['issue_type'] == 'VALID').sum()}")
    print(f"  - Valid eastern suburbs: {(investigation_df['issue_type'] == 'VALID_EASTERN_SUBURB').sum()}")
    print(f"  - Out of range: {(investigation_df['issue_type'] == 'OUT_OF_RANGE').sum()}")
    print(f"  - Missing: {(investigation_df['issue_type'] == 'MISSING_COORDINATE').sum()}")
    print(f"  - Suspicious: {(investigation_df['issue_type'].str.contains('SUSPICIOUS')).sum()}")
    
    return investigation_df


def perform_station_eda(investigation_df: pd.DataFrame) -> dict:
    """
    Phase 2: Deep station EDA.
    """
    print("\n" + "=" * 60)
    print("PHASE 2: STATION EDA")
    print("=" * 60)
    
    stations_df = pd.read_csv(DATA_DIR / "mumbai/mumbai_stations_clean.csv")
    
    # Calculate metrics
    total_stations = len(stations_df)
    valid_coords = (investigation_df['issue_type'].isin(['VALID', 'VALID_EASTERN_SUBURB'])).sum()
    flagged_coords = total_stations - valid_coords
    
    # Coordinate completeness
    missing_coords = (investigation_df['issue_type'] == 'MISSING_COORDINATE').sum()
    coord_completeness = ((total_stations - missing_coords) / total_stations) * 100
    
    # Name analysis
    unique_names = stations_df['station_name'].nunique()
    duplicate_names = stations_df['station_name'].duplicated().sum()
    
    # Coordinate duplicates
    coord_pairs = stations_df[['latitude', 'longitude']].round(6)
    duplicate_coords = coord_pairs.duplicated().sum()
    
    # Bounding box (valid coords only)
    valid_stations = stations_df.merge(
        investigation_df[investigation_df['issue_type'].isin(['VALID', 'VALID_EASTERN_SUBURB'])][['station_id']],
        on='station_id'
    )
    
    if len(valid_stations) > 0:
        lat_min = valid_stations['latitude'].min()
        lat_max = valid_stations['latitude'].max()
        lon_min = valid_stations['longitude'].min()
        lon_max = valid_stations['longitude'].max()
        lat_range = lat_max - lat_min
        lon_range = lon_max - lon_min
    else:
        lat_min = lat_max = lon_min = lon_max = lat_range = lon_range = None
    
    # Compile EDA results
    eda_results = {
        'total_stations': total_stations,
        'valid_coordinates': valid_coords,
        'flagged_coordinates': flagged_coords,
        'missing_coordinates': missing_coords,
        'coordinate_completeness_pct': round(coord_completeness, 2),
        'unique_station_names': unique_names,
        'duplicate_station_names': duplicate_names,
        'duplicate_coordinates': duplicate_coords,
        'latitude_min': lat_min,
        'latitude_max': lat_max,
        'longitude_min': lon_min,
        'longitude_max': lon_max,
        'latitude_range_deg': round(lat_range, 4) if lat_range else None,
        'longitude_range_deg': round(lon_range, 4) if lon_range else None,
    }
    
    # Save as CSV
    eda_df = pd.DataFrame([{
        'metric': k,
        'value': v,
        'system': 'Mumbai Suburban'
    } for k, v in eda_results.items()])
    
    eda_df.to_csv(EDA_DIR / "mumbai_station_eda.csv", index=False)
    
    print("✓ Station EDA complete")
    print(f"  - Total stations: {total_stations}")
    print(f"  - Valid coordinates: {valid_coords} ({valid_coords/total_stations*100:.1f}%)")
    print(f"  - Flagged coordinates: {flagged_coords}")
    print(f"  - Coordinate completeness: {coord_completeness:.1f}%")
    
    return eda_results


def perform_line_eda() -> dict:
    """
    Phase 3: Rail line/network EDA.
    
    Analyzes line geometry from GeoJSON (since CSV geometry_wkt is empty).
    """
    print("\n" + "=" * 60)
    print("PHASE 3: LINE/NETWORK EDA")
    print("=" * 60)
    
    # Load line GeoJSON
    lines_gdf = gpd.read_file(DATA_DIR / "geospatial/mumbai_lines.geojson")
    
    total_segments = len(lines_gdf)
    
    # Calculate segment lengths (in meters, approximate)
    # GeoJSON is in EPSG:4326, convert to EPSG:3857 for length in meters
    lines_gdf_proj = lines_gdf.to_crs(epsg=3857)
    lines_gdf_proj['length_m'] = lines_gdf_proj.geometry.length
    
    # Aggregate metrics
    total_length_m = lines_gdf_proj['length_m'].sum()
    total_length_km = total_length_m / 1000
    min_length_m = lines_gdf_proj['length_m'].min()
    max_length_m = lines_gdf_proj['length_m'].max()
    mean_length_m = lines_gdf_proj['length_m'].mean()
    median_length_m = lines_gdf_proj['length_m'].median()
    
    # Geometry validity
    invalid_geoms = (~lines_gdf.geometry.is_valid).sum()
    empty_geoms = lines_gdf.geometry.is_empty.sum()
    
    # Line name distribution
    line_name_counts = lines_gdf['line_name'].value_counts()
    
    eda_results = {
        'total_line_segments': total_segments,
        'total_network_length_km': round(total_length_km, 2),
        'min_segment_length_m': round(min_length_m, 2),
        'max_segment_length_m': round(max_length_m, 2),
        'mean_segment_length_m': round(mean_length_m, 2),
        'median_segment_length_m': round(median_length_m, 2),
        'invalid_geometries': invalid_geoms,
        'empty_geometries': empty_geoms,
        'unique_line_names': len(line_name_counts)
    }
    
    # Save EDA
    eda_df = pd.DataFrame([{
        'metric': k,
        'value': v,
        'system': 'Mumbai Suburban'
    } for k, v in eda_results.items()])
    
    eda_df.to_csv(EDA_DIR / "mumbai_line_eda.csv", index=False)
    
    # Save line name distribution
    line_name_counts.to_csv(EDA_DIR / "mumbai_line_name_distribution.csv", header=['count'])
    
    print("✓ Line EDA complete")
    print(f"  - Total segments: {total_segments}")
    print(f"  - Network length: {total_length_km:.2f} km")
    print(f"  - Segment length range: {min_length_m:.0f} - {max_length_m:.0f} m")
    print(f"  - Line names: {line_name_counts.to_dict()}")
    
    return eda_results


def analyze_station_spacing(investigation_df: pd.DataFrame) -> pd.DataFrame:
    """
    Phase 4: Station spacing analysis.
    
    Calculate nearest-neighbor distances for valid stations only.
    """
    print("\n" + "=" * 60)
    print("PHASE 4: STATION SPACING ANALYSIS")
    print("=" * 60)
    
    stations_df = pd.read_csv(DATA_DIR / "mumbai/mumbai_stations_clean.csv")
    
    # Filter to valid coordinates only
    valid_stations = stations_df.merge(
        investigation_df[investigation_df['issue_type'].isin(['VALID', 'VALID_EASTERN_SUBURB'])][['station_id']],
        on='station_id'
    )
    
    if len(valid_stations) < 2:
        print("⚠ Not enough valid stations for spacing analysis")
        return pd.DataFrame()
    
    # Create GeoDataFrame
    geometry = [Point(xy) for xy in zip(valid_stations['longitude'], valid_stations['latitude'])]
    gdf = gpd.GeoDataFrame(valid_stations, geometry=geometry, crs='EPSG:4326')
    
    # Project to meters
    gdf_proj = gdf.to_crs(epsg=3857)
    
    spacing_results = []
    
    for idx, station in gdf_proj.iterrows():
        # Find nearest neighbor
        other_stations = gdf_proj[gdf_proj['station_id'] != station['station_id']]
        
        if len(other_stations) == 0:
            continue
            
        distances = other_stations.geometry.distance(station.geometry)
        nearest_idx = distances.idxmin()
        nearest_dist_m = distances.loc[nearest_idx]
        nearest_id = other_stations.loc[nearest_idx, 'station_id']
        nearest_name = other_stations.loc[nearest_idx, 'station_name']
        
        spacing_results.append({
            'station_id': station['station_id'],
            'station_name': station['station_name'],
            'nearest_station_id': nearest_id,
            'nearest_station_name': nearest_name,
            'nearest_distance_m': round(nearest_dist_m, 2)
        })
    
    spacing_df = pd.DataFrame(spacing_results)
    
    # Save spacing analysis
    spacing_df.to_csv(EDA_DIR / "mumbai_station_spacing.csv", index=False)
    
    # Calculate aggregate metrics
    min_spacing = spacing_df['nearest_distance_m'].min()
    median_spacing = spacing_df['nearest_distance_m'].median()
    mean_spacing = spacing_df['nearest_distance_m'].mean()
    max_spacing = spacing_df['nearest_distance_m'].max()
    
    # Flag unusually close stations (< 500m)
    close_stations = spacing_df[spacing_df['nearest_distance_m'] < 500]
    
    print("✓ Station spacing analysis complete")
    print(f"  - Stations analyzed: {len(spacing_df)}")
    print(f"  - Spacing range: {min_spacing:.0f} - {max_spacing:.0f} m")
    print(f"  - Median spacing: {median_spacing:.0f} m")
    print(f"  - Mean spacing: {mean_spacing:.0f} m")
    print(f"  - Unusually close pairs (< 500m): {len(close_stations)}")
    
    return spacing_df


def create_infrastructure_features(investigation_df: pd.DataFrame, spacing_df: pd.DataFrame) -> pd.DataFrame:
    """
    Phase 5: Create station-level infrastructure features.
    
    Features are DATA-DRIVEN only. No fabrication.
    """
    print("\n" + "=" * 60)
    print("PHASE 5: INFRASTRUCTURE FEATURE ENGINEERING")
    print("=" * 60)
    
    stations_df = pd.read_csv(DATA_DIR / "mumbai/mumbai_stations_clean.csv")
    
    # Merge investigation results
    features_df = stations_df.merge(investigation_df[['station_id', 'issue_type']], on='station_id')
    
    # Add coordinate validity flag
    features_df['coordinate_valid'] = features_df['issue_type'].isin(['VALID', 'VALID_EASTERN_SUBURB'])
    
    # Add spacing if available
    if len(spacing_df) > 0:
        features_df = features_df.merge(
            spacing_df[['station_id', 'nearest_distance_m']],
            on='station_id',
            how='left'
        )
    else:
        features_df['nearest_distance_m'] = None
    
    # Line association: NOT AVAILABLE in current data
    # KML has line names but no station-to-line mapping
    features_df['line_id'] = None
    features_df['line_name'] = None
    
    # Service features: UNAVAILABLE
    features_df['trains_per_day'] = None
    features_df['peak_frequency_min'] = None
    features_df['service_hours'] = None
    
    # Ridership: UNAVAILABLE
    features_df['daily_ridership'] = None
    features_df['annual_ridership'] = None
    
    # Select final feature set
    feature_cols = [
        'station_id',
        'station_name',
        'latitude',
        'longitude',
        'coordinate_valid',
        'nearest_distance_m',
        'line_id',
        'line_name',
        'source',
        'source_file',
        'source_url'
    ]
    
    final_features = features_df[feature_cols]
    
    # Save features
    final_features.to_csv(FEATURES_DIR / "mumbai_station_features.csv", index=False)
    
    print("✓ Infrastructure features created")
    print(f"  - Features: {len(feature_cols)} columns")
    print(f"  - Stations: {len(final_features)}")
    print("  - Available features: station_id, name, coords, validity, spacing")
    print("  - Unavailable features: line association, service data, ridership")
    
    return final_features


def create_network_features(line_eda: dict) -> pd.DataFrame:
    """
    Phase 6: Create network-level features.
    """
    print("\n" + "=" * 60)
    print("PHASE 6: NETWORK-LEVEL FEATURES")
    print("=" * 60)
    
    # Load spacing for aggregate stats
    if (EDA_DIR / "mumbai_station_spacing.csv").exists():
        spacing_df = pd.read_csv(EDA_DIR / "mumbai_station_spacing.csv")
        median_spacing_m = spacing_df['nearest_distance_m'].median()
        mean_spacing_m = spacing_df['nearest_distance_m'].mean()
    else:
        median_spacing_m = None
        mean_spacing_m = None
    
    # Load investigation for valid coord count
    investigation_df = pd.read_csv(REPORTS_DIR / "mumbai_coordinate_investigation.csv")
    valid_coords = (investigation_df['issue_type'].isin(['VALID', 'VALID_EASTERN_SUBURB'])).sum()
    
    network_features = {
        'system': 'Mumbai Suburban',
        'state': 'Maharashtra',
        'city': 'Mumbai',
        'total_stations': len(investigation_df),
        'valid_stations': valid_coords,
        'network_length_km': line_eda.get('total_network_length_km'),
        'total_line_segments': line_eda.get('total_line_segments'),
        'median_station_spacing_m': round(median_spacing_m, 2) if median_spacing_m else None,
        'mean_station_spacing_m': round(mean_spacing_m, 2) if mean_spacing_m else None,
        'station_density_per_km': round(valid_coords / line_eda['total_network_length_km'], 2) if line_eda['total_network_length_km'] else None,
        'coordinate_coverage_pct': round((valid_coords / len(investigation_df)) * 100, 2)
    }
    
    network_df = pd.DataFrame([network_features])
    network_df.to_csv(FEATURES_DIR / "mumbai_network_features.csv", index=False)
    
    print("✓ Network features created")
    print(f"  - Network length: {network_features['network_length_km']} km")
    print(f"  - Station density: {network_features['station_density_per_km']:.2f} stations/km")
    print(f"  - Median spacing: {network_features['median_station_spacing_m']} m")
    
    return network_df


def create_data_availability_matrix():
    """
    Phase 7: Document data availability for all systems.
    """
    print("\n" + "=" * 60)
    print("PHASE 7: DATA AVAILABILITY MATRIX")
    print("=" * 60)
    
    systems = [
        {
            'system': 'Mumbai Suburban',
            'state': 'Maharashtra',
            'city': 'Mumbai',
            'stations': 'AVAILABLE',
            'coordinates': 'PARTIAL',  # 67.9% valid
            'line_geometry': 'AVAILABLE',
            'route_data': 'UNKNOWN',  # Line names present but no station-to-line mapping
            'service_data': 'UNAVAILABLE',
            'timetable': 'UNAVAILABLE',
            'frequency': 'UNAVAILABLE',
            'ridership': 'UNAVAILABLE',
            'population': 'NOT_YET_JOINED',
            'lgd': 'NOT_YET_JOINED',
            'accessibility': 'NOT_YET_CALCULATED',
            'status': 'PARTIAL'
        },
        {
            'system': 'Chennai Suburban',
            'state': 'Tamil Nadu',
            'city': 'Chennai',
            'stations': 'UNAVAILABLE',
            'coordinates': 'UNAVAILABLE',
            'line_geometry': 'UNAVAILABLE',
            'route_data': 'UNAVAILABLE',
            'service_data': 'UNAVAILABLE',
            'timetable': 'UNAVAILABLE',
            'frequency': 'UNAVAILABLE',
            'ridership': 'UNAVAILABLE',
            'population': 'NOT_YET_JOINED',
            'lgd': 'NOT_YET_JOINED',
            'accessibility': 'NOT_YET_CALCULATED',
            'status': 'DATA_UNAVAILABLE'
        },
        {
            'system': 'Kolkata Suburban',
            'state': 'West Bengal',
            'city': 'Kolkata',
            'stations': 'UNAVAILABLE',
            'coordinates': 'UNAVAILABLE',
            'line_geometry': 'UNAVAILABLE',
            'route_data': 'UNAVAILABLE',
            'service_data': 'UNAVAILABLE',
            'timetable': 'UNAVAILABLE',
            'frequency': 'UNAVAILABLE',
            'ridership': 'UNAVAILABLE',
            'population': 'NOT_YET_JOINED',
            'lgd': 'NOT_YET_JOINED',
            'accessibility': 'NOT_YET_CALCULATED',
            'status': 'DATA_UNAVAILABLE'
        },
        {
            'system': 'Hyderabad MMTS',
            'state': 'Telangana',
            'city': 'Hyderabad',
            'stations': 'UNAVAILABLE',
            'coordinates': 'UNAVAILABLE',
            'line_geometry': 'UNAVAILABLE',
            'route_data': 'UNAVAILABLE',
            'service_data': 'UNAVAILABLE',
            'timetable': 'UNAVAILABLE',
            'frequency': 'UNAVAILABLE',
            'ridership': 'UNAVAILABLE',
            'population': 'NOT_YET_JOINED',
            'lgd': 'NOT_YET_JOINED',
            'accessibility': 'NOT_YET_CALCULATED',
            'status': 'DATA_UNAVAILABLE'
        },
        {
            'system': 'Pune Suburban',
            'state': 'Maharashtra',
            'city': 'Pune',
            'stations': 'UNAVAILABLE',
            'coordinates': 'UNAVAILABLE',
            'line_geometry': 'UNAVAILABLE',
            'route_data': 'UNAVAILABLE',
            'service_data': 'UNAVAILABLE',
            'timetable': 'UNAVAILABLE',
            'frequency': 'UNAVAILABLE',
            'ridership': 'UNAVAILABLE',
            'population': 'NOT_YET_JOINED',
            'lgd': 'NOT_YET_JOINED',
            'accessibility': 'NOT_YET_CALCULATED',
            'status': 'DATA_UNAVAILABLE'
        }
    ]
    
    matrix_df = pd.DataFrame(systems)
    matrix_df.to_csv(DATA_DIR / "local_rail_m2_data_matrix.csv", index=False)
    
    print("✓ Data availability matrix created")
    print(f"  - Systems documented: {len(systems)}")
    print("  - Mumbai: PARTIAL (stations + geometry, no service/ridership)")
    print("  - Others: DATA_UNAVAILABLE")
    
    return matrix_df


def main():
    """Execute complete M2 pipeline."""
    print("\n" + "=" * 60)
    print("LOCAL RAIL M2 — DEEP EDA + NETWORK ANALYSIS + FEATURES")
    print("=" * 60)
    print("Starting M2 pipeline...\n")
    
    # Phase 1: Coordinate investigation
    investigation_df = investigate_coordinate_quality()
    
    # Phase 2: Station EDA
    station_eda = perform_station_eda(investigation_df)
    
    # Phase 3: Line EDA
    line_eda = perform_line_eda()
    
    # Phase 4: Station spacing
    spacing_df = analyze_station_spacing(investigation_df)
    
    # Phase 5: Station features
    create_infrastructure_features(investigation_df, spacing_df)
    
    # Phase 6: Network features
    create_network_features(line_eda)
    
    # Phase 7: Data availability matrix
    create_data_availability_matrix()
    
    print("\n" + "=" * 60)
    print("M2 PIPELINE COMPLETE")
    print("=" * 60)
    print(f"Mumbai: {station_eda['valid_coordinates']} valid stations, {line_eda['total_network_length_km']:.2f} km network")
    print("Other cities: DATA_UNAVAILABLE")
    print(f"Files created: {len(list(EDA_DIR.glob('*')))} EDA, {len(list(FEATURES_DIR.glob('*')))} features")
    print("\nExit Code: 0")


if __name__ == "__main__":
    main()
