"""Shared layers used by every field: states, population, cities, built-up history.

Each loader reads a file fetched by `python -m common.fetch` and fails loudly if it is missing.
"""

from __future__ import annotations

import io
import re
import zipfile
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
from rasterio.warp import transform_bounds
from rasterio.windows import from_bounds

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"

# Metric CRS for distances and lengths across India (Lambert conformal conic, WGS 84).
INDIA_CRS = "EPSG:7755"
INDIA_BOUNDS = (68.0, 6.0, 98.0, 37.5)  # lon/lat bbox incl. islands

CANONICAL_STATES = [
    "Andaman and Nicobar Islands", "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar",
    "Chandigarh", "Chhattisgarh", "Dadra and Nagar Haveli and Daman and Diu", "Delhi", "Goa",
    "Gujarat", "Haryana", "Himachal Pradesh", "Jammu and Kashmir", "Jharkhand", "Karnataka",
    "Kerala", "Ladakh", "Lakshadweep", "Madhya Pradesh", "Maharashtra", "Manipur", "Meghalaya",
    "Mizoram", "Nagaland", "Odisha", "Puducherry", "Punjab", "Rajasthan", "Sikkim", "Tamil Nadu",
    "Telangana", "Tripura", "Uttar Pradesh", "Uttarakhand", "West Bengal",
]
_ALIASES = {
    "andaman and nicobar": "Andaman and Nicobar Islands",
    "andaman and nicobar island": "Andaman and Nicobar Islands",
    "a and n islands": "Andaman and Nicobar Islands",
    "chattisgarh": "Chhattisgarh",
    "dadra and nagar haveli": "Dadra and Nagar Haveli and Daman and Diu",
    "daman and diu": "Dadra and Nagar Haveli and Daman and Diu",
    "daman diu": "Dadra and Nagar Haveli and Daman and Diu",
    "dnh and dd": "Dadra and Nagar Haveli and Daman and Diu",
    "d and n haveli and daman and diu": "Dadra and Nagar Haveli and Daman and Diu",
    "the dadra and nagar haveli and daman and diu": "Dadra and Nagar Haveli and Daman and Diu",
    "nct of delhi": "Delhi",
    "delhi nct": "Delhi",
    "j and k": "Jammu and Kashmir",
    "orissa": "Odisha",
    "panjab": "Punjab",
    "pondicherry": "Puducherry",
    "tamilnadu": "Tamil Nadu",
    "telengana": "Telangana",
    "uttaranchal": "Uttarakhand",
}
_BY_KEY = {s.lower(): s for s in CANONICAL_STATES}


def normalize_state(name: object) -> str | None:
    """Canonical state/UT name for the many spellings used across sources; None if unknown."""
    if name is None or (isinstance(name, float) and np.isnan(name)):
        return None
    key = str(name).lower().replace("&", " and ")
    key = " ".join(re.sub(r"[^a-z ]", " ", key).split())
    return _BY_KEY.get(key) or _ALIASES.get(key)


def _require(path: Path) -> Path:
    if not path.exists():
        raise FileNotFoundError(f"{path} missing — run: cd ml && uv run python -m common.fetch")
    return path


def load_states() -> gpd.GeoDataFrame:
    """State/UT polygons (DataMeet) with a canonical `state` column, EPSG:4326."""
    gdf = gpd.read_file(_require(RAW / "datameet" / "States" / "Admin2.shp"))
    name_col = next(c for c in gdf.columns if c.upper() in ("ST_NM", "STATE", "STATE_NAME", "NAME_1"))
    gdf["state"] = gdf[name_col].map(normalize_state)
    unknown = sorted(gdf.loc[gdf["state"].isna(), name_col].astype(str).unique())
    if unknown:
        raise ValueError(f"unmapped state names in DataMeet boundaries: {unknown}")
    gdf = gdf.to_crs("EPSG:4326").dissolve(by="state", as_index=False)[["state", "geometry"]]
    return gdf


def load_population_points() -> pd.DataFrame:
    """WorldPop 2020 1 km pixels with people > 0: columns lon, lat, pop."""
    path = _require(RAW / "worldpop" / "ind_ppp_2020_1km_Aggregated_UNadj.tif")
    with rasterio.open(path) as src:
        band = src.read(1, masked=True)
        rows, cols = np.nonzero(~band.mask & (band.filled(0) > 0))
        xs, ys = rasterio.transform.xy(src.transform, rows, cols, offset="center")
        return pd.DataFrame({
            "lon": np.asarray(xs, dtype="float64"),
            "lat": np.asarray(ys, dtype="float64"),
            "pop": band.data[rows, cols].astype("float64"),
        })


def load_cities(min_population: int = 100_000) -> pd.DataFrame:
    """Indian places from GeoNames cities15000 with population >= min_population."""
    path = _require(RAW / "geonames" / "cities15000.zip")
    columns = [
        "geonameid", "name", "asciiname", "alternatenames", "lat", "lon", "feature_class",
        "feature_code", "country", "cc2", "admin1", "admin2", "admin3", "admin4", "population",
        "elevation", "dem", "timezone", "modified",
    ]
    with zipfile.ZipFile(path) as zf, zf.open("cities15000.txt") as f:
        df = pd.read_csv(io.TextIOWrapper(f, encoding="utf-8"), sep="\t", header=None,
                         names=columns, usecols=["geonameid", "asciiname", "lat", "lon",
                                                 "country", "population", "feature_code"],
                         keep_default_na=False, dtype={"country": str})
    df = df[(df["country"] == "IN") & (df["population"] >= min_population)]
    return df.rename(columns={"asciiname": "name"}).sort_values("population", ascending=False)


def read_ghsl_built(year: int, bounds_lonlat: tuple[float, float, float, float] = INDIA_BOUNDS):
    """GHSL built-up surface (m² per 1 km cell) for a lon/lat window.

    Returns (array float32, affine transform, CRS). Read straight from the zip — no unpacking.
    """
    name = f"GHS_BUILT_S_E{year}_GLOBE_R2023A_54009_1000_V1_0"
    path = _require(RAW / "ghsl" / f"{name}.zip")
    with rasterio.open(f"zip://{path}!{name}.tif") as src:
        left, bottom, right, top = transform_bounds("EPSG:4326", src.crs, *bounds_lonlat)
        window = from_bounds(left, bottom, right, top, src.transform).round_offsets().round_lengths()
        data = src.read(1, window=window, masked=True).filled(0).astype("float32")
        return data, src.window_transform(window), src.crs
