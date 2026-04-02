# Design Journal: SQL Query Intelligence Platform

This journal documents the evolution of the SQL Query Analyzer, from a monolithic prototype (v0) to a distributed, production-grade telemetry pipeline (v1).

## Session 1: The Monolithic Prototype (v0)
### Initial Understanding
The goal was a multi-tenant SQL observability platform.
**Assumptions:**
- Tenancy is handled at the database level (Logical Isolation).
- Lineage extraction is recursive (using `sqlglot`).
- AI is an enhancement, not a core requirement for v0.

### Key Decisions
- **FastAPI for Gateway**: Quick development with async support.
- **`sqlmodel` for ORM**: Seamless integration with FastAPI and Pydantic.
- **SQLite Fallback**: In `core/db_manager.py`, I implemented a fallback to SQLite if Postgres is unavailable. This was crucial for initial local development but is a "code smell" for production.

---

### Session 4: Decentralized Isolation & UI Finalization
**Objective:** Finalize the "Post-V0" transition by removing the central bottleneck and closing the UI loop.

#### 1. Pivot to Decentralized Multi-Tenancy
Based on senior-level feedback, we removed the central `Tenants` table from a "Master" database.
- **Why?** Centralized auth lookups are a scalability bottleneck. Moving metadata into the tenant's own database (`tenant_metadata`) ensures true isolation and reduces cross-tenant noise.
- **Routing:** Identity is now asserted via a trusted header (`X-Tenant-ID`), simulating a validated JWT claim from an external IdP (Identity Provider).

#### 2. The Role of "Schema Sync"
We clarified the distinction between **Telemetry** (the query stream) and **Schema Sync** (the metadata layer).
- **Accuracy:** Without "Synced Schema" (CachedAsset), lineage extraction is a guessing game for unqualified columns. By indexing DDL snapshots, the `LineageColumn` worker can resolve `email` to `users` with high confidence.

#### 3. Closing the Observability Loop
The frontend dashboard is now fully wired to the background workers.
- **Asynchronous Results:** The UI handles the "Worker Pending" state gracefully, showing results as they populate the distributed Postgres/SQLite stores.

**Status:** ALL Phase 4 tasks completed. End-to-end verification successful.

---

## Session 2: The Production Scaling Pivot (v1)
### Identifying the Bottleneck
The v0 implementation used FastAPI `BackgroundTasks`. While simple, this is risky for millions of queries because:
1. It shares resources with the API worker pool.
2. It has no persistence; if the server restarts, tasks are lost.
3. It cannot scale horizontally.

### Architectural Shift
I've decided to move to a **Distributed Task Queue** architecture using **RQ (Redis Queue)** and a high-volume timeseries sink in **Elasticsearch**.

**Reference Implementation Changes:**
- **[MODIFY] `gateway/main.py`**: Replacing `BackgroundTasks` with a Redis-backed queue.
- **[NEW] `workers/worker.py`**: A standalone worker process that pulls from Redis.
- **[IMPLEMENT] `workers/processor.py`**: Activating the Elasticsearch sink for high-volume ingest.

### Trade-offs: Latency vs. Durability
By using a queue, we increase the end-to-end latency for AI suggestions (from sub-second to sub-5-second), but we ensure that not a single query metric is lost during a traffic spike of 10M+ queries.

---

## Session 3: Data Lifecycle & Cold Storage (v2)
**Objective:** Solve the "Forever Growth" problem of query telemetry.
### Hot-to-Cold Archival Logic
We implemented a **30-day Data Lifecycle Management (DLM)** policy.
- **Hot Tier:** Postgres (Last 30 days) for sub-second dashboard performance.
- **Cold Tier:** MinIO (S3-compatible) as compressed **Parquet** files.
- **Why Parquet?** It provides columnar compression and is natively searchable by tools like Presto/Trino if the user needs to audit historical data without impacting the production database.

### The "Shadow Schema" Hurdle
During development, we encountered a mismatch where the physical database was missing `first_seen_at`. 
- **AI Influence:** I used Antigravity's agentic tools to execute a direct `ALTER TABLE` across the tenant isolation boundary, resolving a "Dashboard Empty" bug that would have stalled manual development for hours.

---

## Tool Usage Reflection
I've leveraged AI tools (specifically Antigravity/Gemini) to:
- **Architecture Steerage:** Deciding to use SHA256 hashing for query idempotency (`query_text + dialect + schema_version`) to prevent duplicate analysis costs.
- **Refactoring:** Converting monolithic SQLite code into a decentralized Postgres/Redis orchestrator.
- **Precision Debugging:** Identifying a `DeserializationError` in the RQ worker caused by missing `__init__.py` files across package boundaries.

### AI Integration Strategy (Stretch Goal)
Our AI Tier is intentionally decoupled via Redis.
- **Vision:** In a v3 world, the "AI Optimizer" wouldn't just suggest SQL; it would automatically submit Pull Requests to the user's DBT/Looker repository to apply the performance indexes it discovered.

---
*Last updated: 2026-04-03*
