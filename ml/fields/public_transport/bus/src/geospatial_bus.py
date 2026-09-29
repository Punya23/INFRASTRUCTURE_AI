import pandas as pd
from pathlib import Path
import json

PROCESSED_DIR = Path("ml/fields/public_transport/bus/data/processed")
REPORTS_DIR = Path("ml/fields/public_transport/bus/reports")
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

def create_geometries():
    print("Generating GeoJSON for bus stops...")
    stops_file = PROCESSED_DIR / "bus_stops_clean.csv"
        
    num_stops = 0
    if stops_file.exists():
        stops = pd.read_csv(stops_file)
        valid_stops = stops[(stops['stop_lat'] >= -90) & (stops['stop_lat'] <= 90) & 
                            (stops['stop_lon'] >= -180) & (stops['stop_lon'] <= 180)].copy()
        
        features = []
        for _, row in valid_stops.iterrows():
            features.append({
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [row['stop_lon'], row['stop_lat']]
                },
                "properties": {
                    "stop_id": row.get('stop_id'),
                    "stop_name": row.get('stop_name')
                }
            })
            
        geojson = {
            "type": "FeatureCollection",
            "features": features
        }
        
        with open(PROCESSED_DIR / "bus_stops.geojson", "w") as f:
            json.dump(geojson, f)
            
        num_stops = len(features)
        print(f"Generated bus_stops.geojson with {num_stops} points.")
        
        # Mock spatial join since geography polygons are not available
        print("Creating mocked LGD mapping (no geometries in shared geography layer)...")
        lgd_mapping = valid_stops[['stop_id', 'stop_name', 'stop_lat', 'stop_lon']].copy()
        lgd_mapping.rename(columns={'stop_lat': 'latitude', 'stop_lon': 'longitude'}, inplace=True)
        lgd_mapping['state_code'] = None
        lgd_mapping['state_name'] = None
        lgd_mapping['district_code'] = None
        lgd_mapping['district_name'] = None
        lgd_mapping['subdistrict_code'] = None
        lgd_mapping['subdistrict_name'] = None
        lgd_mapping['ulb_code'] = None
        lgd_mapping['ulb_name'] = None
        lgd_mapping['ward_code'] = None
        lgd_mapping['ward_name'] = None
        
        lgd_mapping.to_csv(PROCESSED_DIR / "bus_stops_lgd_mapping.csv", index=False)
        print("Generated bus_stops_lgd_mapping.csv")

    else:
        print(f"File {stops_file} not found.")
        
    # Routes geometry
    print("Generating GeoJSON for bus routes (derived from stops)...")
    stop_times_file = PROCESSED_DIR / "bus_stop_times_clean.csv"
    trips_file = PROCESSED_DIR / "bus_trips_clean.csv"

    num_routes = 0
    if stop_times_file.exists() and stops_file.exists() and trips_file.exists():
        st = pd.read_csv(stop_times_file)
        stops = pd.read_csv(stops_file)
        trips = pd.read_csv(trips_file)
        
        st = st.merge(stops[['stop_id', 'stop_lat', 'stop_lon']], on='stop_id', how='left')
        st = st.dropna(subset=['stop_lat', 'stop_lon'])
        st = st.sort_values(['trip_id', 'stop_sequence'])
        
        trip_to_route = dict(zip(trips['trip_id'], trips['route_id']))
        st['route_id'] = st['trip_id'].map(trip_to_route)
        
        features = []
        routes_data = []
        
        for route_id, route_st in st.groupby('route_id'):
            trip_counts = route_st['trip_id'].value_counts()
            if trip_counts.empty: continue
            best_trip = trip_counts.index[0]
            
            best_st = route_st[route_st['trip_id'] == best_trip]
            if len(best_st) > 1:
                coords = [[lon, lat] for lon, lat in zip(best_st['stop_lon'], best_st['stop_lat'])]
                features.append({
                    "type": "Feature",
                    "geometry": {
                        "type": "LineString",
                        "coordinates": coords
                    },
                    "properties": {
                        "route_id": route_id,
                        "derived_from_stops": True
                    }
                })
                routes_data.append({
                    'route_id': route_id,
                    'representative_trip': best_trip,
                    'derived_from_stops': True
                })
                
        if features:
            geojson = {
                "type": "FeatureCollection",
                "features": features
            }
            with open(PROCESSED_DIR / "bus_routes.geojson", "w") as f:
                json.dump(geojson, f)
            num_routes = len(features)
            print(f"Generated bus_routes.geojson with {num_routes} lines.")
            
            route_mapping = pd.DataFrame(routes_data)
            route_mapping.to_csv(PROCESSED_DIR / "bus_route_lgd_mapping.csv", index=False)
            print("Generated bus_route_lgd_mapping.csv")
    else:
        print("Missing files for route generation.")
        
    summary = {
        "total_mapped_stops": num_stops,
        "total_unmatched_stops": num_stops,
        "total_routes_derived": num_routes,
        "ulb_coverage": "N/A - No boundaries",
        "district_coverage": "N/A - No boundaries"
    }
    pd.DataFrame([summary]).to_csv(PROCESSED_DIR / "bus_spatial_summary.csv", index=False)
    print("Generated bus_spatial_summary.csv")

if __name__ == "__main__":
    create_geometries()
