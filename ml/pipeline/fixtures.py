"""Write UI fixtures (docs/fields/README.md: shared layer contract, ≤ 5 MB per file)."""

from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import shapely


def write_geojson(gdf: gpd.GeoDataFrame, path: Path, max_mb: float = 5.0) -> None:
    """Compact GeoJSON on a ≈11 m grid; raises if the file exceeds max_mb (simplify more upstream)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    gdf = gdf.set_geometry(shapely.set_precision(gdf.geometry.values, 1e-4))
    gdf = gdf[~gdf.geometry.is_empty]
    path.write_text(gdf.to_json(drop_id=True, separators=(",", ":")))
    size = path.stat().st_size / 1e6
    if size > max_mb:
        raise ValueError(f"{path.name} is {size:.1f} MB (limit {max_mb} MB) — simplify geometry more")
    print(f"fixture {path.name}: {len(gdf):,} features, {size:.1f} MB")
