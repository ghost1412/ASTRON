# Design Journal: SQL Query Intelligence Platform

This journal documents the evolution of the SQL Query Analyzer, from my monolithic blueprint (v0) to a distributed, production-grade microservice mesh (v3).

---

## Session 1: High-Level Blueprints (v0)
### Architectural Strategy
The goal was a multi-tenant SQL observability platform with strict logical isolation and high-volume throughput. 

**Core Blueprints:**
- Tenancy is logically isolated at the database level.
- Lineage extraction is recursive (leveraging `sqlglot` for ## 🏛️ Database Strategy: The Bimodal Mesh (v8.3)

ASTRON employs a professional, dual-layered database strategy to achieve both **ACID consistency** and **hyper-scale observability**.

### 1. PostgreSQL | The Management Plane (Sharded)
- **Authoritative Record**: Stores the absolute state of Queries, Lineage Columns, and AI Suggestions.
- **Tenant Isolation**: Every organization has its own sharded database instance.
- **Consistency**: Used by the Discovery Hub to ensure that every "Intelligence Pull Request" is based on transactional truth.

### 2. Elasticsearch | The Observability Plane (Global)
- **Time-Series Scale**: Indices every telemetry sample (metrics) to support sub-second aggregations.
- **Global Search**: Architected to handle fuzzy-text analysis across all shards without impacting the transaction log of the production databases.
- **Discovery Power**: Handles broad, cross-tenant trend analysis and high-volume metric ingestion (2-3M+ events/day).

### 3. Redis | The Orchestration Layer
- **RQ Worker Sync**: Manages the priority-sharded task queues for the AI analysis workers.
- **Distributed Locks**: Prevents "Discovery Collisions" during massive schema re-syncs.
- Minimal v0 structure to prioritize core ingestion first.

### Implementation Highlights
- **FastAPI Skeleton**: Drafted the initial gateway structure with modular routing.
- **ORM Schema**: Implemented `sqlmodel` definitions for multi-tenant metadata and query tracking.
- **SQLite Fallback**: Included a local development fallback mechanism to allow rapid prototyping before Postgres integration.


---

## Session 2: Distributed Scaling (v1)
### Scaling Strategy
As the system grew, the resource bottleneck of the API Gateway necessitated a move to a **Distributed Task Queue** architecture using **RQ (Redis Queue)** and a high-volume timeseries sink in **Elasticsearch**.


### Implementation Highlights
- **Queue Plumbing**: Developed Redis-backed queue logic in `gateway/main.py` for asynchronous processing.
- **Worker Skeleton**: Built standalone `workers/worker.py` for a decoupled processing pool.


---

## Session 3: Data Lifecycle & Cold Storage (v2)
### The "Forever Growth" Solution
I defined the **30-day Data Lifecycle Management (DLM)** policy to ensure infrastructure sustainability. 

### Implementation Highlights
- **Parquet Export**: Implemented **compressed Parquet** export logic for efficient columnar storage.
- **MinIO Orchestration**: Integrated S3-compatible cold storage (MinIO) for long-term telemetry retention.


---

## Session 4: Decentralized Isolation & Mesh (v3)
### The Final Leap
To ensure absolute tenant isolation, the platform moved from a "Master DB" to a **Shared-Nothing Orchestration**, leveraging a **Containerized Mesh**.


### Implementation Highlights
- **Persona-based Docker Image**: Designed a multi-persona Dockerfile for modular service deployment.
- **Mesh Orchestration**: Configured container networking and service discovery in `docker-compose.yaml` to unify the system mesh.


---

## Technical Reference

### Core Data Models

| Model | Purpose | Key Attributes |
|---|---|---|
| `TenantMetadata` | Multi-tenant identity storage | `company_id`, `company_name`, `admin_email` |
| `Query` | Canonical query registry | `query_hash`, `query_text`, `dialect`, `db_alias` |
| `QueryMetric` | Execution telemetry | `calls`, `total_exec_time_ms`, `timestamp` |
| `LineageColumn` | Recursive AST analysis results | `asset_name`, `column_name`, `clause_type` |
| `QuerySuggestion` | Intelligence & Optimization state | `status`, `suggestions`, `error` |

### API Specification (v1)

- `POST /v1/onboarding/register`: Provisions a new isolated database shard for a tenant.
- `GET /v1/stats`: Aggregates real-time metrics (Query count, Lineage nodes) from the tenant's shard.
- `POST /v1/assets`: Ingests structural metadata (DDL) for lineage resolution.
- `POST /v1/telemetry/queries/bulk`: High-volume ingestion with fair-share chunking.
- `GET /v1/queries/{query_hash}`: Fetches deep-dive analysis including lineage and optimization.

### System Feature: AI Optimization Strategy
The platform utilizes an asynchronous optimization tier termed "Model Pluralism":
1. **Model Strategy:** Implements a standard `AISuggestionEngine` protocol in `workers/ai_optimization.py`.
2. **Parallel Dispatch:** The Redis Queue allows for "Fan-out" patterns where multiple analysis models can process the same query hash concurrently.
3. **Generic Schema:** The `QuerySuggestion` model uses a discriminator to unify results from various intelligence engines (e.g., Performance, Security, Cost).


---
*Last updated: 2026-04-03*
