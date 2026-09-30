# ADR-0005: PostgreSQL + PostGIS as the only datastore, including the job queue

- Status: Proposed
- Date: 2026-09-28
- Deciders: project team
- Related: docs/PLAN.md §6, §7, §17 · ADR-0006, ADR-0010

## Context

We need spatial queries and vector tiles, fuzzy place-name search (a gazetteer), vector similarity (deduplication, linking news to projects), a durable job queue for chat messages and news, and analytics tables. The team is small, the DPG must be self-hostable, and operations must stay simple.

## Decision

One PostgreSQL database with:

- **PostGIS** — geometry, spatial indexes, `ST_AsMVT` vector tiles;
- **pg_trgm** — the gazetteer and fuzzy name matching;
- **pgvector** — embeddings;
- a **table-based job queue** — `SELECT … FOR UPDATE SKIP LOCKED`, retries with backoff, dead-letter status after 5 attempts.

DuckDB is used only offline in the pipeline, to read large GeoParquet files (Overture) by bounding box. It is not a serving store.

## Consequences

- Good: one backup, one connection string; the queue and the data commit in one transaction, so no message is lost between them; simple local development.
- Bad: the queue has a throughput ceiling (fine up to hundreds of messages per second); vector search at national scale needs HNSW index tuning; one database is a single point of failure — production uses managed Postgres with a replica.

## Alternatives considered

- Kafka or Redis for the queue — another service to run before any measured need.
- Elasticsearch for search — `pg_trgm` is enough for a gazetteer.
- A dedicated vector database — `pgvector` is enough at this scale.
- MongoDB — much weaker spatial analytics than PostGIS.

## Revisit when

Intake sustains more than ~200 messages per second, vector tables pass ~10 million rows with latency problems, or analytics queries slow the serving path (add a read replica first).
