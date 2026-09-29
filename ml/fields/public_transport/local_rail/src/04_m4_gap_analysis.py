#!/usr/bin/env python3
"""
LOCAL RAIL M4 — Infrastructure Gap Analysis

This script performs evidence-based infrastructure gap analysis using ONLY verified
M1, M2, and M3 outputs. NO fabricated data, NO overclaimed conclusions.

Key Principles:
- Distinguish OBSERVED from POTENTIAL_GAP from DATA_BLOCKED
- Every gap requires evidence + threshold + methodology
- Missing data remains NULL (not zero, not estimated)
- Population/service conclusions BLOCKED without data
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple

# Paths
import sys
REPO_ROOT = Path(__file__).resolve().parents[5]
LOCAL_RAIL_BASE = REPO_ROOT / "ml/fields/public_transport/local_rail"

DATA_DIR = LOCAL_RAIL_BASE / "data/processed"
GAPS_DIR = DATA_DIR / "gaps"
FEATURES_DIR = DATA_DIR / "features"
EDA_DIR = DATA_DIR / "eda"
GEOGRAPHY_DIR = DATA_DIR / "geography"
REPORTS_DIR = LOCAL_RAIL_BASE / "reports"

# Create directories
GAPS_DIR.mkdir(parents=True, exist_ok=True)

print(f"Repository root: {REPO_ROOT}")
print(f"Local rail base: {LOCAL_RAIL_BASE}")


def load_verified_data() -> Dict:
    """
    Phase 1: Load all verified M1/M2/M3 outputs.
    """
    print("\n" + "=" * 60)
    print("PHASE 1: LOAD VERIFIED M1/M2/M3 DATA")
    print("=" * 60)
    
    data = {}
    
    # M1/M2 outputs
    data['stations'] = pd.read_csv(DATA_DIR / "mumbai/mumbai_stations_clean.csv")
    data['lines'] = pd.read_csv(DATA_DIR / "mumbai/mumbai_lines_clean.csv")
    data['station_features'] = pd.read_csv(FEATURES_DIR / "mumbai_station_features.csv")
    data['network_features'] = pd.read_csv(FEATURES_DIR / "mumbai_network_features.csv")
    data['station_spacing'] = pd.read_csv(EDA_DIR / "mumbai_station_spacing.csv")
    data['station_eda'] = pd.read_csv(EDA_DIR / "mumbai_station_eda.csv")
    data['line_eda'] = pd.read_csv(EDA_DIR / "mumbai_line_eda.csv")
    
    # M3 outputs
    data['accessibility'] = pd.read_csv(GEOGRAPHY_DIR / "mumbai_accessibility_summary.csv")
    data['station_geography'] = pd.read_csv(FEATURES_DIR / "mumbai_station_geography.csv")
    
    print(f"✓ Loaded verified data:")
    print(f"  - Stations: {len(data['stations'])}")
    print(f"  - Station spacing records: {len(data['station_spacing'])}")
    print(f"  - Network features: {len(data['network_features'])} records")
    print(f"  - Accessibility buffers: {len(data['accessibility'])} types")
    
    return data


def calculate_spacing_distribution(station_spacing: pd.DataFrame) -> Dict:
    """
    Phase 2: Calculate station spacing distribution and thresholds.
    """
    print("\n" + "=" * 60)
    print("PHASE 2: STATION SPACING DISTRIBUTION")
    print("=" * 60)
    
    spacings = station_spacing['nearest_distance_m'].values
    
    distribution = {
        'count': len(spacings),
        'min': spacings.min(),
        'p25': np.percentile(spacings, 25),
        'median': np.median(spacings),
        'p75': np.percentile(spacings, 75),
        'p90': np.percentile(spacings, 90),
        'p95': np.percentile(spacings, 95),
        'max': spacings.max(),
        'mean': spacings.mean(),
        'std': spacings.std()
    }
    
    print(f"✓ Station spacing distribution:")
    print(f"  - Min: {distribution['min']:.0f} m")
    print(f"  - P25: {distribution['p25']:.0f} m")
    print(f"  - Median: {distribution['median']:.0f} m")
    print(f"  - P75: {distribution['p75']:.0f} m")
    print(f"  - P90: {distribution['p90']:.0f} m")
    print(f"  - P95: {distribution['p95']:.0f} m")
    print(f"  - Max: {distribution['max']:.0f} m")
    
    return distribution


def create_infrastructure_indicators(data: Dict, spacing_dist: Dict) -> pd.DataFrame:
    """
    Phase 3: Create infrastructure indicator framework.
    """
    print("\n" + "=" * 60)
    print("PHASE 3: INFRASTRUCTURE INDICATORS")
    print("=" * 60)
    
    network_features = data['network_features'].iloc[0]
    accessibility = data['accessibility']
    
    indicators = []
    
    # Station count
    indicators.append({
        'indicator_id': 'IND_001',
        'indicator_name': 'Total Stations',
        'description': 'Total number of Mumbai suburban railway stations',
        'value': network_features['total_stations'],
        'unit': 'stations',
        'geography': 'Mumbai Suburban Railway Network',
        'source': 'BMC via OpenCity.in',
        'source_url': 'https://data.opencity.in/dataset/mumbai-suburban-network-2025',
        'data_status': 'OBSERVED',
        'calculation_method': 'Count of verified station records from M1/M2',
        'interpretation': 'Number of railway stations in the Mumbai suburban network',
        'limitations': 'None'
    })
    
    # Network length
    indicators.append({
        'indicator_id': 'IND_002',
        'indicator_name': 'Network Length',
        'description': 'Total length of railway line segments',
        'value': network_features['network_length_km'],
        'unit': 'km',
        'geography': 'Mumbai Suburban Railway Network',
        'source': 'BMC via OpenCity.in',
        'source_url': 'https://data.opencity.in/dataset/mumbai-suburban-network-2025',
        'data_status': 'OBSERVED',
        'calculation_method': 'Sum of line segment lengths (M2, projected to EPSG:3857)',
        'interpretation': 'Total track length across Western, Central, Harbour, and Trans-Harbour lines',
        'limitations': 'Line segments may not represent exact track layout'
    })
    
    # Median station spacing
    indicators.append({
        'indicator_id': 'IND_003',
        'indicator_name': 'Median Station Spacing',
        'description': 'Median nearest-neighbor distance between stations',
        'value': spacing_dist['median'],
        'unit': 'meters',
        'geography': 'Mumbai Suburban Railway Network',
        'source': 'Derived from BMC station coordinates',
        'source_url': 'https://data.opencity.in/dataset/mumbai-suburban-network-2025',
        'data_status': 'DERIVED',
        'calculation_method': 'Median of nearest-neighbor distances (M2, UTM Zone 43N)',
        'interpretation': 'Typical distance between adjacent stations',
        'limitations': 'Nearest-neighbor may not reflect actual route sequence'
    })
    
    # P90 spacing threshold
    indicators.append({
        'indicator_id': 'IND_004',
        'indicator_name': 'P90 Station Spacing',
        'description': '90th percentile station spacing (threshold for large gaps)',
        'value': spacing_dist['p90'],
        'unit': 'meters',
        'geography': 'Mumbai Suburban Railway Network',
        'source': 'Derived from BMC station coordinates',
        'source_url': 'https://data.opencity.in/dataset/mumbai-suburban-network-2025',
        'data_status': 'DERIVED',
        'calculation_method': '90th percentile of nearest-neighbor distances',
        'interpretation': 'Stations above this spacing are in the top 10% for large gaps',
        'limitations': 'Statistical threshold, not a normative standard'
    })
    
    # P95 spacing threshold
    indicators.append({
        'indicator_id': 'IND_005',
        'indicator_name': 'P95 Station Spacing',
        'description': '95th percentile station spacing (threshold for very large gaps)',
        'value': spacing_dist['p95'],
        'unit': 'meters',
        'geography': 'Mumbai Suburban Railway Network',
        'source': 'Derived from BMC station coordinates',
        'source_url': 'https://data.opencity.in/dataset/mumbai-suburban-network-2025',
        'data_status': 'DERIVED',
        'calculation_method': '95th percentile of nearest-neighbor distances',
        'interpretation': 'Stations above this spacing are in the top 5% for very large gaps',
        'limitations': 'Statistical threshold, not a normative standard'
    })
    
    # Station density
    indicators.append({
        'indicator_id': 'IND_006',
        'indicator_name': 'Station Density by Network Extent',
        'description': 'Stations per kilometer of network',
        'value': network_features['station_density_per_km'],
        'unit': 'stations/km',
        'geography': 'Mumbai Suburban Railway Network',
        'source': 'Derived from BMC data',
        'source_url': 'https://data.opencity.in/dataset/mumbai-suburban-network-2025',
        'data_status': 'DERIVED',
        'calculation_method': 'Total stations / Network length',
        'interpretation': 'Average number of stations per km of track',
        'limitations': 'Network length includes all line segments; actual unique track length may differ'
    })
    
    # Catchments
    for _, row in accessibility.iterrows():
        buffer_m = row['buffer_m']
        indicators.append({
            'indicator_id': f'IND_00{7 + int(buffer_m/500) - 1}',
            'indicator_name': f'Theoretical Geographic Catchment ({buffer_m}m)',
            'description': f'Total area within {buffer_m}m of any station (theoretical)',
            'value': row['coverage_area_km2'],
            'unit': 'km²',
            'geography': 'Mumbai Suburban Railway Network',
            'source': 'Generated from BMC station coordinates (M3)',
            'source_url': 'N/A',
            'data_status': 'DERIVED',
            'calculation_method': f'Circular buffers of {buffer_m}m radius around each station (UTM Zone 43N), sum of areas',
            'interpretation': f'THEORETICAL geographic coverage within {buffer_m}m walking/cycling distance. NOT actual transit accessibility.',
            'limitations': 'Overlapping catchments counted multiple times; physical barriers not considered; service frequency unavailable'
        })
    
    indicators_df = pd.DataFrame(indicators)
    indicators_df.to_csv(GAPS_DIR / "mumbai_infrastructure_indicators.csv", index=False)
    
    print(f"✓ Infrastructure indicators created:")
    print(f"  - Total indicators: {len(indicators_df)}")
    print(f"  - OBSERVED: {(indicators_df['data_status'] == 'OBSERVED').sum()}")
    print(f"  - DERIVED: {(indicators_df['data_status'] == 'DERIVED').sum()}")
    
    return indicators_df


def identify_potential_spacing_gaps(data: Dict, spacing_dist: Dict) -> pd.DataFrame:
    """
    Phase 4: Identify potential geographic spacing gaps.
    """
    print("\n" + "=" * 60)
    print("PHASE 4: POTENTIAL SPACING GAP IDENTIFICATION")
    print("=" * 60)
    
    station_spacing = data['station_spacing'].copy()
    
    # Use P90 as threshold for "large spacing"
    # Use P95 as threshold for "very large spacing"
    p90_threshold = spacing_dist['p90']
    p95_threshold = spacing_dist['p95']
    
    gap_evidence = []
    
    for _, row in station_spacing.iterrows():
        spacing_m = row['nearest_distance_m']
        
        if spacing_m >= p95_threshold:
            gap_evidence.append({
                'gap_id': f"GAP_{row['station_id']}",
                'station_id': row['station_id'],
                'station_name': row['station_name'],
                'nearest_station_id': row['nearest_station_id'],
                'nearest_station_name': row['nearest_station_name'],
                'gap_type': 'VERY_LARGE_STATION_SPACING',
                'indicator_id': 'IND_005',
                'indicator_value': spacing_m,
                'threshold': p95_threshold,
                'threshold_method': 'P95 (95th percentile of station spacing distribution)',
                'evidence': f'Station is {spacing_m:.0f}m from nearest neighbor, above P95 threshold ({p95_threshold:.0f}m)',
                'status': 'POTENTIAL_GEOGRAPHIC_GAP',
                'confidence': 'MEDIUM',
                'source': 'BMC via OpenCity.in',
                'source_url': 'https://data.opencity.in/dataset/mumbai-suburban-network-2025',
                'limitations': 'Geographic spacing only; population impact unknown (no population data); service quality unknown (no frequency data)'
            })
        elif spacing_m >= p90_threshold:
            gap_evidence.append({
                'gap_id': f"GAP_{row['station_id']}",
                'station_id': row['station_id'],
                'station_name': row['station_name'],
                'nearest_station_id': row['nearest_station_id'],
                'nearest_station_name': row['nearest_station_name'],
                'gap_type': 'LARGE_STATION_SPACING',
                'indicator_id': 'IND_004',
                'indicator_value': spacing_m,
                'threshold': p90_threshold,
                'threshold_method': 'P90 (90th percentile of station spacing distribution)',
                'evidence': f'Station is {spacing_m:.0f}m from nearest neighbor, above P90 threshold ({p90_threshold:.0f}m)',
                'status': 'POTENTIAL_GEOGRAPHIC_GAP',
                'confidence': 'MEDIUM',
                'source': 'BMC via OpenCity.in',
                'source_url': 'https://data.opencity.in/dataset/mumbai-suburban-network-2025',
                'limitations': 'Geographic spacing only; population impact unknown (no population data); service quality unknown (no frequency data)'
            })
    
    gap_df = pd.DataFrame(gap_evidence)
    gap_df.to_csv(GAPS_DIR / "mumbai_potential_spacing_gaps.csv", index=False)
    
    print(f"✓ Potential spacing gaps identified:")
    print(f"  - P90 threshold: {p90_threshold:.0f} m")
    print(f"  - P95 threshold: {p95_threshold:.0f} m")
    print(f"  - Large spacing (P90+): {(gap_df['gap_type'] == 'LARGE_STATION_SPACING').sum()}")
    print(f"  - Very large spacing (P95+): {(gap_df['gap_type'] == 'VERY_LARGE_STATION_SPACING').sum()}")
    print(f"  - Total potential gaps: {len(gap_df)}")
    
    return gap_df


def create_station_level_indicators(data: Dict, spacing_dist: Dict, gap_evidence: pd.DataFrame) -> pd.DataFrame:
    """
    Phase 5: Create station-level indicator dataset.
    """
    print("\n" + "=" * 60)
    print("PHASE 5: STATION-LEVEL INDICATORS")
    print("=" * 60)
    
    station_geography = data['station_geography'].copy()
    station_spacing = data['station_spacing'].copy()
    
    # Station geography already has nearest_distance_m from M2
    # Just add nearest station details from spacing data
    station_indicators = station_geography.merge(
        station_spacing[['station_id', 'nearest_station_id', 'nearest_station_name']],
        on='station_id',
        how='left'
    )
    
    # Categorize spacing
    p90_threshold = spacing_dist['p90']
    p95_threshold = spacing_dist['p95']
    median_threshold = spacing_dist['median']
    
    def categorize_spacing(spacing_m):
        if pd.isna(spacing_m):
            return 'UNKNOWN'
        elif spacing_m >= p95_threshold:
            return 'VERY_LARGE_SPACING'
        elif spacing_m >= p90_threshold:
            return 'LARGE_SPACING'
        elif spacing_m >= median_threshold:
            return 'ABOVE_MEDIAN_SPACING'
        else:
            return 'BELOW_MEDIAN_SPACING'
    
    station_indicators['station_spacing_status'] = station_indicators['nearest_distance_m'].apply(categorize_spacing)
    
    # Add potential gap flag
    gap_station_ids = set(gap_evidence['station_id'].unique())
    station_indicators['potential_spacing_gap'] = station_indicators['station_id'].isin(gap_station_ids)
    
    # Network edge detection (stations at min/max lat/lon extremes)
    # Simple method: stations in outer 10% of lat/lon range
    lat_range = station_indicators['latitude'].max() - station_indicators['latitude'].min()
    lon_range = station_indicators['longitude'].max() - station_indicators['longitude'].min()
    lat_min_threshold = station_indicators['latitude'].min() + 0.1 * lat_range
    lat_max_threshold = station_indicators['latitude'].max() - 0.1 * lat_range
    lon_min_threshold = station_indicators['longitude'].min() + 0.1 * lon_range
    lon_max_threshold = station_indicators['longitude'].max() - 0.1 * lon_range
    
    station_indicators['network_edge_status'] = (
        (station_indicators['latitude'] < lat_min_threshold) |
        (station_indicators['latitude'] > lat_max_threshold) |
        (station_indicators['longitude'] < lon_min_threshold) |
        (station_indicators['longitude'] > lon_max_threshold)
    )
    
    # Rename for clarity
    station_indicators = station_indicators.rename(columns={
        'catchment_500m_available': 'catchment_500m',
        'catchment_1km_available': 'catchment_1km',
        'catchment_2km_available': 'catchment_2km'
    })
    
    # Add data status columns
    station_indicators['coordinate_status'] = 'OBSERVED'
    station_indicators['population_status'] = 'DATA_UNAVAILABLE'
    station_indicators['frequency_status'] = 'DATA_UNAVAILABLE'
    station_indicators['ridership_status'] = 'DATA_UNAVAILABLE'
    station_indicators['data_confidence'] = 'HIGH'  # For coordinates only
    
    # Select final columns
    final_cols = [
        'station_id', 'station_name', 'latitude', 'longitude',
        'nearest_distance_m', 'nearest_station_id', 'nearest_station_name',
        'station_spacing_status', 'potential_spacing_gap', 'network_edge_status',
        'catchment_500m', 'catchment_1km', 'catchment_2km',
        'coordinate_status', 'data_confidence',
        'population_status', 'frequency_status', 'ridership_status',
        'ward_code', 'ward_name', 'ulb_code', 'ulb_name', 'district_code', 'district_name',
        'join_status', 'source', 'source_file', 'source_url'
    ]
    
    station_indicators = station_indicators[final_cols]
    station_indicators.to_csv(GAPS_DIR / "mumbai_station_level_indicators.csv", index=False)
    
    print(f"✓ Station-level indicators created:")
    print(f"  - Stations: {len(station_indicators)}")
    print(f"  - Very large spacing: {(station_indicators['station_spacing_status'] == 'VERY_LARGE_SPACING').sum()}")
    print(f"  - Large spacing: {(station_indicators['station_spacing_status'] == 'LARGE_SPACING').sum()}")
    print(f"  - Network edge: {station_indicators['network_edge_status'].sum()}")
    print(f"  - Potential gaps flagged: {station_indicators['potential_spacing_gap'].sum()}")
    
    return station_indicators


def create_blocked_indicators_table() -> pd.DataFrame:
    """
    Phase 6: Document BLOCKED indicators (missing required data).
    """
    print("\n" + "=" * 60)
    print("PHASE 6: BLOCKED INDICATORS")
    print("=" * 60)
    
    blocked = [
        {
            'indicator': 'population_per_station',
            'status': 'BLOCKED',
            'reason': 'No population data available',
            'required_data': 'Census population data + spatial boundaries',
            'current_source': 'UNAVAILABLE',
            'use_case': 'Calculate average population served per station'
        },
        {
            'indicator': 'stations_per_100k_population',
            'status': 'BLOCKED',
            'reason': 'No population data available',
            'required_data': 'Census population data + catchment boundaries',
            'current_source': 'UNAVAILABLE',
            'use_case': 'Normalize station count by population'
        },
        {
            'indicator': 'population_within_500m',
            'status': 'BLOCKED',
            'reason': 'No population data + no spatial boundaries',
            'required_data': 'Census population data + ward/ULB polygons',
            'current_source': 'UNAVAILABLE',
            'use_case': 'Calculate population within 500m catchment'
        },
        {
            'indicator': 'population_within_1km',
            'status': 'BLOCKED',
            'reason': 'No population data + no spatial boundaries',
            'required_data': 'Census population data + ward/ULB polygons',
            'current_source': 'UNAVAILABLE',
            'use_case': 'Calculate population within 1km catchment'
        },
        {
            'indicator': 'population_within_2km',
            'status': 'BLOCKED',
            'reason': 'No population data + no spatial boundaries',
            'required_data': 'Census population data + ward/ULB polygons',
            'current_source': 'UNAVAILABLE',
            'use_case': 'Calculate population within 2km catchment'
        },
        {
            'indicator': 'underserved_population',
            'status': 'BLOCKED',
            'reason': 'No population data + no service data',
            'required_data': 'Census population + service frequency + catchment analysis',
            'current_source': 'UNAVAILABLE',
            'use_case': 'Identify high-population areas with poor rail access'
        },
        {
            'indicator': 'ridership_per_station',
            'status': 'BLOCKED',
            'reason': 'No ridership data available',
            'required_data': 'Station-level daily/annual ridership counts',
            'current_source': 'UNAVAILABLE',
            'use_case': 'Calculate demand per station'
        },
        {
            'indicator': 'peak_frequency',
            'status': 'BLOCKED',
            'reason': 'No service frequency data available',
            'required_data': 'Train timetables or frequency data',
            'current_source': 'UNAVAILABLE',
            'use_case': 'Calculate trains per hour during peak times'
        },
        {
            'indicator': 'off_peak_frequency',
            'status': 'BLOCKED',
            'reason': 'No service frequency data available',
            'required_data': 'Train timetables or frequency data',
            'current_source': 'UNAVAILABLE',
            'use_case': 'Calculate trains per hour during off-peak times'
        },
        {
            'indicator': 'first_last_train_times',
            'status': 'BLOCKED',
            'reason': 'No timetable data available',
            'required_data': 'Station-level timetables',
            'current_source': 'UNAVAILABLE',
            'use_case': 'Determine service operating hours'
        },
        {
            'indicator': 'actual_transit_accessibility',
            'status': 'BLOCKED',
            'reason': 'No service frequency data available',
            'required_data': 'Service frequency + operating hours',
            'current_source': 'UNAVAILABLE',
            'use_case': 'Calculate actual accessibility (vs. geographic proximity)'
        },
        {
            'indicator': 'demand_supply_gap',
            'status': 'BLOCKED',
            'reason': 'No ridership + no capacity data',
            'required_data': 'Ridership + train capacity + frequency',
            'current_source': 'UNAVAILABLE',
            'use_case': 'Identify overcrowded vs. underutilized stations'
        },
    ]
    
    blocked_df = pd.DataFrame(blocked)
    blocked_df.to_csv(GAPS_DIR / "mumbai_blocked_indicators.csv", index=False)
    
    print(f"✓ Blocked indicators documented:")
    print(f"  - Total blocked: {len(blocked_df)}")
    print(f"  - Population-related: {blocked_df['indicator'].str.contains('population').sum()}")
    print(f"  - Service-related: {blocked_df['indicator'].str.contains('frequency|transit|timetable').sum()}")
    print(f"  - Ridership-related: {blocked_df['indicator'].str.contains('ridership|demand').sum()}")
    
    return blocked_df


def create_data_completeness_matrix(data: Dict) -> pd.DataFrame:
    """
    Phase 7: Create data completeness matrix.
    """
    print("\n" + "=" * 60)
    print("PHASE 7: DATA COMPLETENESS MATRIX")
    print("=" * 60)
    
    completeness = [
        {
            'indicator': 'Station Coordinates',
            'available': True,
            'status': 'COMPLETE',
            'source': 'BMC via OpenCity.in',
            'required_for_gap_analysis': 'Essential',
            'limitation': 'None'
        },
        {
            'indicator': 'Network Geometry',
            'available': True,
            'status': 'COMPLETE',
            'source': 'BMC via OpenCity.in',
            'required_for_gap_analysis': 'Essential',
            'limitation': 'Line segments may not match exact track layout'
        },
        {
            'indicator': 'Station Spacing',
            'available': True,
            'status': 'COMPLETE',
            'source': 'Derived from coordinates (M2)',
            'required_for_gap_analysis': 'Essential',
            'limitation': 'Nearest-neighbor may not reflect route sequence'
        },
        {
            'indicator': 'Geographic Catchments (500m/1km/2km)',
            'available': True,
            'status': 'COMPLETE',
            'source': 'Generated from coordinates (M3)',
            'required_for_gap_analysis': 'Essential',
            'limitation': 'Theoretical geographic only, not actual transit accessibility'
        },
        {
            'indicator': 'LGD Boundaries (Spatial Polygons)',
            'available': False,
            'status': 'DATA_UNAVAILABLE',
            'source': 'N/A',
            'required_for_gap_analysis': 'High',
            'limitation': 'Cannot perform station-to-geography joins without polygons'
        },
        {
            'indicator': 'Population Data',
            'available': False,
            'status': 'DATA_UNAVAILABLE',
            'source': 'N/A',
            'required_for_gap_analysis': 'High',
            'limitation': 'Cannot calculate catchment population or underserved areas'
        },
        {
            'indicator': 'Service Frequency',
            'available': False,
            'status': 'DATA_UNAVAILABLE',
            'source': 'N/A',
            'required_for_gap_analysis': 'High',
            'limitation': 'Cannot assess actual transit accessibility (only geographic proximity)'
        },
        {
            'indicator': 'Ridership',
            'available': False,
            'status': 'DATA_UNAVAILABLE',
            'source': 'N/A',
            'required_for_gap_analysis': 'Medium',
            'limitation': 'Cannot validate demand or identify overcrowding'
        },
        {
            'indicator': 'Timetable',
            'available': False,
            'status': 'DATA_UNAVAILABLE',
            'source': 'N/A',
            'required_for_gap_analysis': 'Medium',
            'limitation': 'Cannot determine operating hours or first/last trains'
        },
        {
            'indicator': 'Station-Line Mapping',
            'available': False,
            'status': 'PARTIAL',
            'source': 'Line names in KML but no station assignments',
            'required_for_gap_analysis': 'Low',
            'limitation': 'Cannot analyze gaps by specific line (Western vs Central vs Harbour)'
        },
        {
            'indicator': 'Interchange Information',
            'available': False,
            'status': 'DATA_UNAVAILABLE',
            'source': 'N/A',
            'required_for_gap_analysis': 'Low',
            'limitation': 'Cannot identify multimodal transfer stations'
        },
    ]
    
    completeness_df = pd.DataFrame(completeness)
    completeness_df.to_csv(GAPS_DIR / "mumbai_data_completeness.csv", index=False)
    
    print(f"✓ Data completeness matrix created:")
    print(f"  - Total components: {len(completeness_df)}")
    print(f"  - Available (COMPLETE): {(completeness_df['status'] == 'COMPLETE').sum()}")
    print(f"  - Unavailable: {(completeness_df['status'] == 'DATA_UNAVAILABLE').sum()}")
    print(f"  - Partial: {(completeness_df['status'] == 'PARTIAL').sum()}")
    
    return completeness_df


def create_network_gap_summary(data: Dict, spacing_dist: Dict, gap_evidence: pd.DataFrame) -> pd.DataFrame:
    """
    Phase 8: Create network-level gap summary.
    """
    print("\n" + "=" * 60)
    print("PHASE 8: NETWORK-LEVEL GAP SUMMARY")
    print("=" * 60)
    
    network_features = data['network_features'].iloc[0]
    accessibility = data['accessibility']
    station_indicators = pd.read_csv(GAPS_DIR / "mumbai_station_level_indicators.csv")
    
    summary = {
        'system': 'Mumbai Suburban Railway',
        'state': 'Maharashtra',
        'city': 'Mumbai',
        'network_length_km': network_features['network_length_km'],
        'station_count': network_features['total_stations'],
        'median_spacing_m': spacing_dist['median'],
        'p90_spacing_m': spacing_dist['p90'],
        'p95_spacing_m': spacing_dist['p95'],
        'min_spacing_m': spacing_dist['min'],
        'max_spacing_m': spacing_dist['max'],
        'catchment_500m_km2': accessibility[accessibility['buffer_m'] == 500]['coverage_area_km2'].values[0],
        'catchment_1km_km2': accessibility[accessibility['buffer_m'] == 1000]['coverage_area_km2'].values[0],
        'catchment_2km_km2': accessibility[accessibility['buffer_m'] == 2000]['coverage_area_km2'].values[0],
        'potential_gap_station_count': len(gap_evidence),
        'large_spacing_count': (gap_evidence['gap_type'] == 'LARGE_STATION_SPACING').sum(),
        'very_large_spacing_count': (gap_evidence['gap_type'] == 'VERY_LARGE_STATION_SPACING').sum(),
        'network_edge_station_count': station_indicators['network_edge_status'].sum(),
        'population_analysis_status': 'BLOCKED',
        'service_analysis_status': 'BLOCKED',
        'ridership_analysis_status': 'BLOCKED',
        'boundary_join_status': 'BLOCKED',
        'data_completeness_score': f'4/11 components available',
    }
    
    summary_df = pd.DataFrame([summary])
    summary_df.to_csv(GAPS_DIR / "mumbai_network_gap_summary.csv", index=False)
    
    print(f"✓ Network-level gap summary created")
    print(f"  - Network length: {summary['network_length_km']} km")
    print(f"  - Median spacing: {summary['median_spacing_m']:.0f} m")
    print(f"  - P90 spacing: {summary['p90_spacing_m']:.0f} m")
    print(f"  - Potential gaps: {summary['potential_gap_station_count']}")
    
    return summary_df


def main():
    """Execute complete M4 pipeline."""
    print("\n" + "=" * 60)
    print("LOCAL RAIL M4 — INFRASTRUCTURE GAP ANALYSIS")
    print("=" * 60)
    print("Starting M4 pipeline...\n")
    
    # Phase 1: Load verified data
    data = load_verified_data()
    
    # Phase 2: Calculate spacing distribution
    spacing_dist = calculate_spacing_distribution(data['station_spacing'])
    
    # Phase 3: Create infrastructure indicators
    indicators = create_infrastructure_indicators(data, spacing_dist)
    
    # Phase 4: Identify potential spacing gaps
    gap_evidence = identify_potential_spacing_gaps(data, spacing_dist)
    
    # Phase 5: Create station-level indicators
    station_indicators = create_station_level_indicators(data, spacing_dist, gap_evidence)
    
    # Phase 6: Document blocked indicators
    blocked_indicators = create_blocked_indicators_table()
    
    # Phase 7: Create data completeness matrix
    completeness_matrix = create_data_completeness_matrix(data)
    
    # Phase 8: Create network-level gap summary
    network_summary = create_network_gap_summary(data, spacing_dist, gap_evidence)
    
    print("\n" + "=" * 60)
    print("M4 PIPELINE COMPLETE")
    print("=" * 60)
    print(f"Infrastructure indicators: {len(indicators)}")
    print(f"Potential spacing gaps: {len(gap_evidence)}")
    print(f"Blocked indicators: {len(blocked_indicators)}")
    print(f"Data completeness: 4/11 components available")
    print(f"\n**KEY FINDINGS:**")
    print(f"  - P90 spacing threshold: {spacing_dist['p90']:.0f} m")
    print(f"  - P95 spacing threshold: {spacing_dist['p95']:.0f} m")
    print(f"  - Stations with large spacing (P90+): {len(gap_evidence)}")
    print(f"  - Population/service analysis: BLOCKED")
    print(f"\nExit Code: 0")


if __name__ == "__main__":
    main()
