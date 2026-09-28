# ADR-0004: H3 resolution-8 grid as the spatial join key; LGD codes for administrative joins

- Status: Proposed
- Date: 2026-09-28
- Deciders: project team
- Related: README §7, §8.3 · ADR-0003, ADR-0005

## Context

Sources come in incompatible geographies: points, lines, polygons, rasters, wards, districts and free-text place names. Ward boundaries change (delimitation, restructuring), and districts are too coarse inside a city. Hotspot statistics need a regular lattice where every cell has the same neighbors.

## Decision

- **H3 resolution 8** (≈0.74 km² hexagons, ≈460 m edge) is the analysis unit inside cities; **resolution 7** for city overviews; **resolutions 5–6** for state and national views. Resolution is configurable per city.
- H3 ids are computed in Python (`h3-py`) and stored as text next to the hexagon polygon — no dependency on the `h3-pg` extension.
- Distances are measured from hexagon centers to true facility geometries with PostGIS (KNN `<->`), not hexagon to hexagon.
- Administrative joins use **LGD codes**; ward and district figures are area-weighted rollups of hexagons.

## Consequences

- Good: uniform neighborhoods for Gi*; stable when boundaries change; multi-resolution; fast joins; widely known, so easy for contributors.
- Bad: hexagons do not match administrative units, so policy reports need rollups; a single resolution can be too coarse for dense cores and too fine for sparse edges.

## Alternatives considered

- Wards as the unit — unequal sizes, they change over time, and not every city publishes them.
- A square grid (`ST_SquareGrid`) — diagonal neighbors sit at unequal distances.
- `ST_HexagonGrid` — no hierarchy and no global cell id.
- The `h3-pg` extension — convenient, but not available on every managed Postgres.

## Revisit when

The deployment target offers `h3-pg` by default, or ward-level reporting becomes the primary need.
