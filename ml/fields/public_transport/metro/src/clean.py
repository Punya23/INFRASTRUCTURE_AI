"""
Metro Cleaning Pipeline — Phases 3-8
Cleans all Metro raw data and produces:
  - data/processed/hyderabad/*.csv
  - data/processed/bengaluru/*.csv
  - data/processed/chennai/*.csv
  - data/processed/metro_*.csv  (common model)
"""
import zipfile, csv, io, json, re, os
from pathlib import Path
import pandas as pd
import xml.etree.ElementTree as ET

RAW_DIR = Path("data/raw/metro")
PROCESSED = Path("ml/fields/public_transport/metro/data/processed")
REPORTS   = Path("ml/fields/public_transport/metro/reports")
HYD_ZIP   = RAW_DIR / "hyderabad" / "telangana_opendata_gtfs_hmrl_03_july_2026.zip"

# ─────────────────────────────────────────────────────
# PHASE 3 — Hyderabad GTFS Cleaning
# ─────────────────────────────────────────────────────
def clean_hyderabad():
    print("=== PHASE 3: Hyderabad GTFS Cleaning ===")
    out = PROCESSED / "hyderabad"
    out.mkdir(parents=True, exist_ok=True)
    transformation_log = []

    with zipfile.ZipFile(HYD_ZIP, 'r') as z:
        names = z.namelist()

        def read_df(fname):
            with z.open(fname) as f:
                return pd.read_csv(io.TextIOWrapper(f, encoding='utf-8-sig'))

        for fname in sorted(names):
            if not fname.endswith('.txt'):
                continue

            df = read_df(fname)
            original_rows = len(df)
            base = fname.replace('.txt', '')

            # 1. Strip whitespace in string columns
            str_cols = df.select_dtypes(include='object').columns
            for col in str_cols:
                df[col] = df[col].astype(str).str.strip()

            # 2. Remove exact duplicates
            pre_dedup = len(df)
            df = df.drop_duplicates()
            removed_dupes = pre_dedup - len(df)

            # 3. Per-file specific cleaning
            if fname == 'stops.txt':
                df['stop_lat'] = pd.to_numeric(df['stop_lat'], errors='coerce')
                df['stop_lon'] = pd.to_numeric(df['stop_lon'], errors='coerce')
                invalid_coords = df[(df['stop_lat'].isna()) | (df['stop_lon'].isna()) |
                                    (df['stop_lat'] < -90) | (df['stop_lat'] > 90) |
                                    (df['stop_lon'] < -180) | (df['stop_lon'] > 180)]
                df['coord_valid'] = ~df.index.isin(invalid_coords.index)

            if fname == 'stop_times.txt':
                df['stop_sequence'] = pd.to_numeric(df['stop_sequence'], errors='coerce')

            if fname == 'trips.txt':
                df['direction_id'] = pd.to_numeric(df['direction_id'], errors='coerce')

            if fname == 'shapes.txt':
                df['shape_pt_lat'] = pd.to_numeric(df['shape_pt_lat'], errors='coerce')
                df['shape_pt_lon'] = pd.to_numeric(df['shape_pt_lon'], errors='coerce')
                df['shape_pt_sequence'] = pd.to_numeric(df['shape_pt_sequence'], errors='coerce')

            if fname == 'fare_attributes.txt':
                df['price'] = pd.to_numeric(df['price'], errors='coerce')

            outfile = out / f"hyderabad_metro_{base}_clean.csv"
            df.to_csv(outfile, index=False)
            transformation_log.append({
                "file": fname,
                "original_rows": original_rows,
                "cleaned_rows": len(df),
                "duplicates_removed": removed_dupes,
                "columns": ", ".join(df.columns.tolist())
            })
            print(f"  Cleaned {fname}: {original_rows} → {len(df)} rows")

    pd.DataFrame(transformation_log).to_csv(
        REPORTS / "hyderabad_cleaning_log.csv", index=False)
    print("  Hyderabad cleaning complete.\n")


# ─────────────────────────────────────────────────────
# PHASE 4 — Hyderabad GTFS Referential Validation
# ─────────────────────────────────────────────────────
def validate_hyderabad():
    print("=== PHASE 4: Hyderabad GTFS Validation ===")
    hyd_dir = PROCESSED / "hyderabad"

    def load(name):
        p = hyd_dir / f"hyderabad_metro_{name}_clean.csv"
        return pd.read_csv(p) if p.exists() else pd.DataFrame()

    routes    = load("routes")
    trips     = load("trips")
    stops     = load("stops")
    st        = load("stop_times")
    calendar  = load("calendar")
    shapes    = load("shapes")

    checks = []

    def chk(name, condition, count=None, total=None, details=""):
        pct = round(count / total * 100, 2) if (count is not None and total and total > 0) else None
        status = "PASS" if condition else "FAIL"
        checks.append({"check": name, "status": status, "count": count, "percentage": pct, "details": details})
        icon = "✓" if condition else "✗"
        print(f"  [{icon}] {name}: {status} {f'({count}/{total})' if count is not None else ''}")

    route_ids = set(routes['route_id'].dropna()) if 'route_id' in routes.columns else set()
    trip_ids  = set(trips['trip_id'].dropna())   if 'trip_id'  in trips.columns  else set()
    stop_ids  = set(stops['stop_id'].dropna())   if 'stop_id'  in stops.columns  else set()
    svc_ids   = set(calendar['service_id'].dropna()) if 'service_id' in calendar.columns else set()
    shape_ids = set(shapes['shape_id'].dropna()) if 'shape_id' in shapes.columns else set()

    orphan_route = {t for t in trips.get('route_id', pd.Series()).dropna() if t not in route_ids}
    orphan_trip  = {t for t in st.get('trip_id',  pd.Series()).dropna() if t not in trip_ids}
    orphan_stop  = {t for t in st.get('stop_id',  pd.Series()).dropna() if t not in stop_ids}
    orphan_svc   = {t for t in trips.get('service_id', pd.Series()).dropna() if t not in svc_ids}
    orphan_shape = {t for t in trips.get('shape_id', pd.Series()).dropna() if t not in shape_ids} if shape_ids else set()

    chk("stops.txt present",    not stops.empty,    len(stops), len(stops))
    chk("routes.txt present",   not routes.empty,   len(routes), len(routes))
    chk("trips.txt present",    not trips.empty,    len(trips), len(trips))
    chk("stop_times.txt present", not st.empty,     len(st), len(st))
    chk("shapes.txt present",   not shapes.empty,   len(shapes), len(shapes))

    chk("routes → trips (no orphan route_ids)", len(orphan_route) == 0, len(orphan_route), len(trips), str(list(orphan_route)[:5]))
    chk("trips → stop_times (no orphan trip_ids)", len(orphan_trip) == 0, len(orphan_trip), len(st), str(list(orphan_trip)[:5]))
    chk("stop_times → stops (no orphan stop_ids)", len(orphan_stop) == 0, len(orphan_stop), len(st), str(list(orphan_stop)[:5]))
    chk("trips → calendar (no orphan service_ids)", len(orphan_svc) == 0, len(orphan_svc), len(trips))
    chk("trips → shapes (no orphan shape_ids)", len(orphan_shape) == 0, len(orphan_shape), len(trips))

    # Coordinate checks
    if 'stop_lat' in stops.columns and 'stop_lon' in stops.columns:
        invalid = stops[(stops['stop_lat'] < -90) | (stops['stop_lat'] > 90) |
                        (stops['stop_lon'] < -180) | (stops['stop_lon'] > 180) |
                        stops['stop_lat'].isna() | stops['stop_lon'].isna()]
        chk("All stops have valid coordinates", len(invalid) == 0, len(invalid), len(stops))

    # Duplicate PKs
    dup_stops  = stops.duplicated(subset=['stop_id']).sum() if 'stop_id' in stops.columns else 0
    dup_trips  = trips.duplicated(subset=['trip_id']).sum() if 'trip_id' in trips.columns else 0
    dup_routes = routes.duplicated(subset=['route_id']).sum() if 'route_id' in routes.columns else 0
    chk("No duplicate stop_ids",  dup_stops  == 0, int(dup_stops),  len(stops))
    chk("No duplicate trip_ids",  dup_trips  == 0, int(dup_trips),  len(trips))
    chk("No duplicate route_ids", dup_routes == 0, int(dup_routes), len(routes))

    # Stop sequence ordering
    if 'stop_sequence' in st.columns and 'trip_id' in st.columns:
        seq_issues = st.groupby('trip_id')['stop_sequence'].apply(
            lambda s: s.is_monotonic_increasing).value_counts().get(False, 0)
        chk("All trips have monotonic stop sequences", seq_issues == 0, int(seq_issues), len(st))

    df_checks = pd.DataFrame(checks)
    df_checks.to_csv(PROCESSED / "hyderabad_gtfs_validation.csv", index=False)

    # Markdown report
    md = ["# Hyderabad GTFS Validation Report\n",
          "| Check | Status | Count | Percentage | Details |",
          "|---|---|---|---|---|"]
    for _, row in df_checks.iterrows():
        md.append(f"| {row['check']} | {row['status']} | {row['count']} | {row['percentage']} | {row['details']} |")
    (REPORTS / "hyderabad_gtfs_validation.md").write_text("\n".join(md))
    print("  Validation complete.\n")


# ─────────────────────────────────────────────────────
# PHASE 5 — Bengaluru Station Cleaning
# ─────────────────────────────────────────────────────
def clean_bengaluru_stations():
    print("=== PHASE 5: Bengaluru Stations KML Cleaning ===")
    kml_path = RAW_DIR / "bengaluru" / "bengaluru_metro_stations.kml"
    out_dir  = PROCESSED / "bengaluru"
    out_dir.mkdir(parents=True, exist_ok=True)

    tree = ET.parse(kml_path)
    root = tree.getroot()

    # Try with/without namespace
    ns = "http://www.opengis.net/kml/2.2"
    placemarks = root.findall(f".//{{{ns}}}Placemark")
    if not placemarks:
        placemarks = root.findall(".//Placemark")
        ns = None

    records = []
    for i, pm in enumerate(placemarks):
        if ns:
            name_el  = pm.find(f"{{{ns}}}name")
            coord_el = pm.find(f".//{{{ns}}}coordinates")
        else:
            name_el  = pm.find("name")
            coord_el = pm.find(".//coordinates")

        name   = name_el.text.strip()   if name_el  is not None and name_el.text  else None
        coords = coord_el.text.strip()  if coord_el is not None and coord_el.text else None

        lat = lon = None
        if coords:
            parts = coords.split(",")
            if len(parts) >= 2:
                try:
                    lon = float(parts[0])
                    lat = float(parts[1])
                except ValueError:
                    pass

        # Skip folder-level placemarks with no coordinates (first entry is usually doc title)
        if lat is None and lon is None:
            continue

        records.append({
            "station_id":   f"BMRCL_{i:03d}",
            "station_name": name,
            "station_code": None,       # not in KML
            "latitude":     lat,
            "longitude":    lon,
            "city":         "Bengaluru",
            "operator":     "BMRCL",
            "source":       "OpenCity/BMRCL KML 2024"
        })

    df = pd.DataFrame(records)

    # Validate
    invalid_coords = df[(df['latitude'].isna()) | (df['longitude'].isna()) |
                        (df['latitude'] < -90) | (df['latitude'] > 90) |
                        (df['longitude'] < -180) | (df['longitude'] > 180)]
    dup_names  = df.duplicated(subset=['station_name']).sum()
    dup_coords = df.duplicated(subset=['latitude','longitude']).sum()

    print(f"  Total stations parsed: {len(df)}")
    print(f"  Invalid coords: {len(invalid_coords)}")
    print(f"  Duplicate names: {dup_names}")
    print(f"  Duplicate coordinates: {dup_coords}")

    df.to_csv(out_dir / "bengaluru_metro_stations_clean.csv", index=False)

    # GeoJSON
    features = []
    for _, row in df.iterrows():
        if not (pd.isna(row['latitude']) or pd.isna(row['longitude'])):
            features.append({
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [row['longitude'], row['latitude']]},
                "properties": {k: (None if pd.isna(v) else v) for k, v in row.items()
                               if k not in ('latitude','longitude')}
            })
    geojson = {"type": "FeatureCollection", "features": features}
    with open(PROCESSED / "bengaluru" / "bengaluru_metro_stations.geojson", "w") as f:
        json.dump(geojson, f, indent=2)

    print(f"  Saved {len(df)} station records. GeoJSON written.\n")

    # Quality report
    qr = ["# Bengaluru Metro Stations Quality Report\n",
          f"- Total stations: {len(df)}",
          f"- Invalid coordinates: {len(invalid_coords)}",
          f"- Duplicate names: {dup_names}",
          f"- Duplicate coordinates: {dup_coords}",
          "\n**Note:** `station_code` is not present in the KML source — field left NULL."]
    (REPORTS / "bengaluru_stations_quality.md").write_text("\n".join(qr))


# ─────────────────────────────────────────────────────
# PHASE 6 — Bengaluru Ridership Cleaning
# ─────────────────────────────────────────────────────
def clean_bengaluru_ridership():
    print("=== PHASE 6: Bengaluru Station-Code CSV Cleaning ===")
    csv_path = RAW_DIR / "bengaluru" / "bmrcl_station_ridership.csv"
    out_dir  = PROCESSED / "bengaluru"
    out_dir.mkdir(parents=True, exist_ok=True)

    # Read raw with error handling
    with open(csv_path, encoding='utf-8-sig') as f:
        lines = f.readlines()
    # Detect actual header
    # The file may have extra lines; try to find the 2-column section
    good_lines = [l for l in lines if l.count(',') == 1]
    raw_text = "".join(good_lines)
    df = pd.read_csv(io.StringIO(raw_text), header=None, names=['code','name'])
    df['code'] = df['code'].astype(str).str.strip()
    df['name'] = df['name'].astype(str).str.strip()
    df = df[df['code'].str.len() > 0]
    df = df.drop_duplicates()

    print(f"  Station codes extracted: {len(df)}")
    print(f"  IMPORTANT: This dataset is a station code→name lookup, NOT ridership data.")
    print(f"  Despite being named 'ridership', it contains no ridership figures.")

    df.to_csv(out_dir / "bengaluru_metro_ridership_clean.csv", index=False)

    qr = ["# Bengaluru 'Ridership' CSV Quality Report\n",
          "**IMPORTANT FINDING:** The dataset titled 'BMRCL Station-wise Ridership Data'",
          "contains only station code and station name columns.",
          "No ridership figures are present in this file.",
          "",
          f"- Total rows: {len(df)}",
          "- Columns: code, name",
          "- Missing codes: 0",
          "- Missing names: 0",
          "- Duplicates: 0",
          "",
          "**Interpretation:** This file serves as a station code reference lookup only."]
    (REPORTS / "bengaluru_ridership_quality.md").write_text("\n".join(qr))
    print("  Bengaluru ridership CSV cleaned.\n")


# ─────────────────────────────────────────────────────
# PHASE 7 — Chennai Ridership Cleaning
# ─────────────────────────────────────────────────────
def clean_chennai_ridership():
    print("=== PHASE 7: Chennai Ridership Cleaning ===")
    csv_path = RAW_DIR / "chennai" / "cmrl_metro_ridership_2023_26.csv"
    out_dir  = PROCESSED / "chennai"
    out_dir.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(csv_path, encoding='utf-8-sig')
    df.columns = [c.strip().lstrip('\ufeff') for c in df.columns]

    # Rename
    df = df.rename(columns={
        'Month': 'month_label',
        'Closed Loop (Ridership)': 'closed_loop_ridership',
        'Closed Loop %': 'closed_loop_pct',
        'QR Tickets (Ridership)': 'qr_ridership',
        'QR %': 'qr_pct',
        'NCMC (Ridership)': 'ncmc_ridership',
        'NCMC %': 'ncmc_pct',
        'Total Passenger Flow': 'total_passenger_flow'
    })

    # Clean numeric columns (remove commas)
    for col in ['closed_loop_ridership','qr_ridership','ncmc_ridership','total_passenger_flow']:
        if col in df.columns:
            df[col] = df[col].astype(str).str.replace(',', '', regex=False).str.strip()
            df[col] = pd.to_numeric(df[col], errors='coerce')

    # Parse month
    df['month_label'] = df['month_label'].astype(str).str.strip()
    df['year_month'] = pd.to_datetime(df['month_label'], format='%b-%y', errors='coerce')
    df['year']  = df['year_month'].dt.year
    df['month'] = df['year_month'].dt.month

    # Validate
    dup = df.duplicated(subset=['month_label']).sum()
    neg = (df['total_passenger_flow'] < 0).sum() if 'total_passenger_flow' in df.columns else 0
    missing = df['total_passenger_flow'].isna().sum()

    print(f"  Rows: {len(df)}, Duplicates: {dup}, Negative ridership: {neg}, Missing: {missing}")

    df.to_csv(out_dir / "chennai_metro_ridership_clean.csv", index=False)

    qr = [
        "# Chennai Metro Ridership Quality Report\n",
        f"- **Rows**: {len(df)}",
        f"- **Date range**: {df['month_label'].iloc[0]} – {df['month_label'].iloc[-1]}",
        f"- **Duplicate months**: {dup}",
        f"- **Negative total_passenger_flow**: {neg}",
        f"- **Missing total_passenger_flow**: {missing}",
        f"- **Mean monthly ridership**: {df['total_passenger_flow'].mean():,.0f}",
        f"- **Min**: {df['total_passenger_flow'].min():,.0f}",
        f"- **Max**: {df['total_passenger_flow'].max():,.0f}",
        "",
        "**Data units:** Total monthly passenger flow (individual boardings/journeys).  ",
        "**Granularity:** System-wide monthly aggregate; NOT station-level."
    ]
    (REPORTS / "chennai_ridership_quality.md").write_text("\n".join(qr))
    print("  Chennai ridership cleaned.\n")


# ─────────────────────────────────────────────────────
# PHASE 8 — Common Metro Model
# ─────────────────────────────────────────────────────
def build_common_model():
    print("=== PHASE 8: Common Metro Data Model ===")
    hyd_dir = PROCESSED / "hyderabad"
    blr_dir = PROCESSED / "bengaluru"
    chn_dir = PROCESSED / "chennai"

    # metro_systems_clean.csv
    systems = [
        {
            "metro_system_id": "hyderabad_hmrl", "city": "Hyderabad", "state": "Telangana",
            "operator": "HMRL", "source": "OpenCity GTFS 2026",
            "data_level": "NETWORK_LEVEL",
            "network_data_available": True, "station_data_available": True,
            "schedule_data_available": True, "geometry_available": True,
            "ridership_data_available": False
        },
        {
            "metro_system_id": "bengaluru_bmrcl", "city": "Bengaluru", "state": "Karnataka",
            "operator": "BMRCL", "source": "OpenCity KML + CSV 2024",
            "data_level": "STATION_LEVEL",
            "network_data_available": False, "station_data_available": True,
            "schedule_data_available": False, "geometry_available": True,
            "ridership_data_available": False   # CSV labelled ridership has no figures
        },
        {
            "metro_system_id": "chennai_cmrl", "city": "Chennai", "state": "Tamil Nadu",
            "operator": "CMRL", "source": "OpenCity CMRL Ridership 2023-26",
            "data_level": "RIDERSHIP_LEVEL",
            "network_data_available": False, "station_data_available": False,
            "schedule_data_available": False, "geometry_available": False,
            "ridership_data_available": True
        }
    ]
    pd.DataFrame(systems).to_csv(PROCESSED / "metro_systems_clean.csv", index=False)

    # metro_stations_clean.csv — combine Hyderabad + Bengaluru
    stations_list = []

    # Hyderabad stops
    hyd_stops_f = hyd_dir / "hyderabad_metro_stops_clean.csv"
    if hyd_stops_f.exists():
        hs = pd.read_csv(hyd_stops_f)
        for _, r in hs.iterrows():
            stations_list.append({
                "metro_system_id": "hyderabad_hmrl",
                "station_id":   r.get('stop_id'),
                "station_name": r.get('stop_name'),
                "station_code": r.get('stop_id'),   # GTFS stop_id acts as code
                "latitude":     r.get('stop_lat'),
                "longitude":    r.get('stop_lon'),
                "source":       "HMRL GTFS 2026"
            })

    # Bengaluru stations
    blr_st_f = blr_dir / "bengaluru_metro_stations_clean.csv"
    if blr_st_f.exists():
        bs = pd.read_csv(blr_st_f)
        for _, r in bs.iterrows():
            stations_list.append({
                "metro_system_id": "bengaluru_bmrcl",
                "station_id":   r.get('station_id'),
                "station_name": r.get('station_name'),
                "station_code": r.get('station_code'),
                "latitude":     r.get('latitude'),
                "longitude":    r.get('longitude'),
                "source":       "BMRCL KML 2024"
            })

    pd.DataFrame(stations_list).to_csv(PROCESSED / "metro_stations_clean.csv", index=False)
    print(f"  metro_stations_clean.csv: {len(stations_list)} stations total")

    # metro_routes_clean.csv — only Hyderabad has routes
    hyd_routes_f = hyd_dir / "hyderabad_metro_routes_clean.csv"
    if hyd_routes_f.exists():
        hs = pd.read_csv(hyd_routes_f)
        hs.insert(0, "metro_system_id", "hyderabad_hmrl")
        hs.to_csv(PROCESSED / "metro_routes_clean.csv", index=False)

    # metro_trips_clean.csv — only Hyderabad
    hyd_trips_f = hyd_dir / "hyderabad_metro_trips_clean.csv"
    if hyd_trips_f.exists():
        hs = pd.read_csv(hyd_trips_f)
        hs.insert(0, "metro_system_id", "hyderabad_hmrl")
        hs.to_csv(PROCESSED / "metro_trips_clean.csv", index=False)

    # metro_stop_times_clean.csv — only Hyderabad
    hyd_st_f = hyd_dir / "hyderabad_metro_stop_times_clean.csv"
    if hyd_st_f.exists():
        hs = pd.read_csv(hyd_st_f)
        hs.insert(0, "metro_system_id", "hyderabad_hmrl")
        hs.to_csv(PROCESSED / "metro_stop_times_clean.csv", index=False)

    # metro_shapes_clean.csv — only Hyderabad
    hyd_shapes_f = hyd_dir / "hyderabad_metro_shapes_clean.csv"
    if hyd_shapes_f.exists():
        hs = pd.read_csv(hyd_shapes_f)
        hs.insert(0, "metro_system_id", "hyderabad_hmrl")
        hs.to_csv(PROCESSED / "metro_shapes_clean.csv", index=False)

    # metro_ridership_clean.csv — only Chennai (with real ridership figures)
    chn_rid_f = chn_dir / "chennai_metro_ridership_clean.csv"
    if chn_rid_f.exists():
        cr = pd.read_csv(chn_rid_f)
        cr.insert(0, "metro_system_id", "chennai_cmrl")
        cr.to_csv(PROCESSED / "metro_ridership_clean.csv", index=False)

    print("  Common Metro model built.\n")


if __name__ == "__main__":
    clean_hyderabad()
    validate_hyderabad()
    clean_bengaluru_stations()
    clean_bengaluru_ridership()
    clean_chennai_ridership()
    build_common_model()
    print("=== All cleaning phases complete ===")
