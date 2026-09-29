import json
import os
from pathlib import Path

def create_notebook(filename, cells):
    nb = {
        "cells": [],
        "metadata": {},
        "nbformat": 4,
        "nbformat_minor": 5
    }
    
    for cell_type, source in cells:
        cell = {
            "cell_type": cell_type,
            "metadata": {},
            "source": [line + "\n" for line in source.split('\n')[:-1]] + [source.split('\n')[-1]]
        }
        if cell_type == "code":
            cell["execution_count"] = None
            cell["outputs"] = []
        nb["cells"].append(cell)
        
    with open(filename, "w") as f:
        json.dump(nb, f, indent=1)

def generate_gtfs_eda():
    cells = [
        ("markdown", "# TGSRTC GTFS EDA\nExploratory Data Analysis of TGSRTC GTFS feed."),
        ("code", "import pandas as pd\nimport matplotlib.pyplot as plt\nfrom pathlib import Path\n\nPROCESSED_DIR = Path('../data/processed')"),
        ("markdown", "## 1. Stops"),
        ("code", "stops = pd.read_csv(PROCESSED_DIR / 'stops_clean.csv')\nprint(f'Total stops: {len(stops)}')\nprint(f'Unique stops: {stops.stop_id.nunique()}')\nprint('Missing coords:', stops['stop_lat'].isnull().sum())\nprint('Duplicate coords:', stops.duplicated(subset=['stop_lat', 'stop_lon']).sum())"),
        ("markdown", "## 2. Routes"),
        ("code", "routes = pd.read_csv(PROCESSED_DIR / 'routes_clean.csv')\nprint(f'Total routes: {len(routes)}')\nprint('Route Types:')\nprint(routes['route_type'].value_counts())\nroutes['route_type'].value_counts().plot(kind='bar')\nplt.title('Routes by Type')\nplt.show()"),
        ("markdown", "## 3. Trips"),
        ("code", "trips = pd.read_csv(PROCESSED_DIR / 'trips_clean.csv')\nprint(f'Total trips: {len(trips)}')\ntrips_per_route = trips.groupby('route_id').size()\nprint('Trips per route (top 5):')\nprint(trips_per_route.sort_values(ascending=False).head())\ntrips_per_route.plot(kind='hist', bins=50)\nplt.title('Trips per Route')\nplt.show()"),
        ("markdown", "## 4. Stop Times"),
        ("code", "stop_times = pd.read_csv(PROCESSED_DIR / 'stop_times_clean.csv')\nprint(f'Stop time records: {len(stop_times)}')\nstops_per_trip = stop_times.groupby('trip_id').size()\nprint(f'Avg stops per trip: {stops_per_trip.mean():.1f}')\nprint(f'Min stops: {stops_per_trip.min()}, Max stops: {stops_per_trip.max()}')\nstops_per_trip.plot(kind='hist', bins=50)\nplt.title('Stops per Trip')\nplt.show()"),
        ("markdown", "## 5. Calendar"),
        ("code", "calendar = pd.read_csv(PROCESSED_DIR / 'calendar_clean.csv')\nprint('Service Days:')\nprint(calendar[['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']].sum())")
    ]
    create_notebook("../notebooks/01_tgsrtc_gtfs_eda.ipynb", cells)
    
def generate_fleet_eda():
    cells = [
        ("markdown", "# Smart Cities Bus Fleet EDA\nExploratory Data Analysis of Smart Cities Fleet Data."),
        ("code", "import pandas as pd\nimport matplotlib.pyplot as plt\nfrom pathlib import Path\n\nPROCESSED_DIR = Path('../data/processed')"),
        ("markdown", "## 1. Fleet Overview"),
        ("code", "fleet = pd.read_csv(PROCESSED_DIR / 'smartcities_bus_fleet_clean.csv')\nprint(f'Total records: {len(fleet)}')\nprint(f'Cities represented: {fleet[\"City Name\"].nunique()}')\nprint('Missing values:')\nprint(fleet.isnull().sum())"),
        ("markdown", "## 2. Fleet by City"),
        ("code", "city_totals = fleet.groupby('City Name')['No. of buses of that type'].sum().sort_values(ascending=False)\nprint('Top 10 Cities by Fleet:')\nprint(city_totals.head(10))\ncity_totals.head(15).plot(kind='bar', figsize=(10,5))\nplt.title('Top 15 Smart Cities by Bus Fleet')\nplt.ylabel('Number of Buses')\nplt.show()"),
        ("markdown", "## 3. Bus Types"),
        ("code", "type_totals = fleet.groupby('Type Of Bus (Ac / Non Ac)')['No. of buses of that type'].sum()\nprint(type_totals)\ntype_totals.plot(kind='pie', autopct='%1.1f%%')\nplt.title('Bus Fleet by Type')\nplt.show()")
    ]
    create_notebook("../notebooks/02_bus_fleet_eda.ipynb", cells)

def generate_stops_eda():
    cells = [
        ("markdown", "# TGSRTC Stops EDA\nExploratory Data Analysis of TGSRTC Hyderabad Stops CSV."),
        ("code", "import pandas as pd\nfrom pathlib import Path\n\nPROCESSED_DIR = Path('../data/processed')"),
        ("markdown", "## 1. Overview"),
        ("code", "stops = pd.read_csv(PROCESSED_DIR / 'tgsrtc_stops_clean.csv')\nprint(f'Total stops: {len(stops)}')\nprint(f'Unique stop IDs: {stops.stop_id.nunique()}')\nprint('Missing values:')\nprint(stops.isnull().sum())\nprint(f'Duplicate coordinates: {stops.duplicated(subset=[\"stop_lat\", \"stop_lon\"]).sum()}')"),
        ("markdown", "## 2. Geography"),
        ("code", "print('Latitude bounds:', stops.stop_lat.min(), '-', stops.stop_lat.max())\nprint('Longitude bounds:', stops.stop_lon.min(), '-', stops.stop_lon.max())")
    ]
    create_notebook("../notebooks/03_tgsrtc_stops_eda.ipynb", cells)

if __name__ == '__main__':
    os.chdir(Path(__file__).parent)
    generate_gtfs_eda()
    generate_fleet_eda()
    generate_stops_eda()
    print("Notebooks created.")
