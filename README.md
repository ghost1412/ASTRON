# SQL Query Intelligence Platform (Next-Gen)

A production-grade, multi-tenant SQL observability and lineage platform. Designed to scale from 10 queries to 10M+ queries per day using a distributed telemetry pipeline.

---

## 🚀 Evaluator QuickStart (3 Minutes)

1.  **Stop Local Services**: Ensure no local Postgres (5432) or Redis (6379) are running on your host.
2.  **Boot the Mesh**: 
    ```bash
    ./verify_platform.sh
    ```
3.  **Run the Demo**:
    ```bash
    pip install -r requirements.txt
    python3 exporters/demo_exporter.py
    ```
4.  **View UI**: Open `frontend/index.html` in your browser. All metrics and query insights are now live.

> [!IMPORTANT]
> **Port Conflicts**: This platform binds to ports `5432` (Postgres), `6379` (Redis), `9000` (MinIO), and `8000` (Gateway). Please ensure these are free before running `docker-compose`.

---

## 🏛️ Architectural Overview
A high-volume telemetry pipeline for SQL query observability, lineage extraction, and intelligent optimization. Designed for multi-tenancy with logical database isolation.
 10M+ queries per day using a distributed telemetry pipeline.

---

## 🏗️ Architectural Vision: From Prototype to Production

### 1. Your Interpretation
I interpreted this "vague problem" as a requirement for a **Scalable Telemetry Pipeline** rather than a simple CRUD app. 
- **Assumptions:** 
    - Queries are high-frequency, low-latency events.
    - Lineage analysis is CPU-intensive and must be offloaded.
    - Tenancy requires strict logical isolation (Database-per-Tenant) to satisfy enterprise security audits.

### 2. Incremental Evolution
- **v0 (Development):** Monolithic FastAPI + SQLite. Local lineage parsing.
- **v1 (Operational):** Transition to **PostgreSQL** for multi-tenancy. Decentralized metadata management.
- **v2 (Scalable):** Distributed Task Queue using **Redis (RQ)**. Asynchronous Lineage & AI workers. **Elasticsearch** timeseries sink for high-volume metric aggregation.
- **v3 (Enterprise):** **Data Lifecycle Management (DLM)**. Auto-archiving telemetry >30 days## Architecture (Microservice Mesh)
- **Inbound Telemetry**: Decoupled from core processing. Gateway accepts telemetry and places it on **Redis (RQ)**.
- **worker-analysis**: A standalone microservice that consumes the queue for Lineage and AI.
- **dlm-archiver**: A standalone persona for Data Lifecycle Management (Hot-to-Cold migration).
- **Multi-Tenancy**: Logical Database-Per-Tenant isolation via **PostgreSQL**.

## Project Structure
- `gateway/`: Persona for REST API and Onboarding.
- `workers/`: Persona definitions for `analysis` and `archival`.
- `core/`: Shared data models and multi-tenant mesh discovery.
- `docker-compose.yaml`: Infrastructure and Service Orchestration.
```bash
docker-compose up -d
# Services: Postgres (storage), Redis (queue), MinIO (archive), Elasticsearch (metrics)
```

## 🛡️ Scalability & Resilience

The platform is designed for high-availability and horizontal scaling:

- **Self-Healing**: All microservices are configured with `restart: always`. If a process crashes, the Docker engine automatically reboots the container.
- **Horizontal Scaling**: To double or triple your query processing capacity, simply scale the worker pool:
  ```bash
  docker-compose up --scale analysis-worker=3 -d
  ```
- **Stateless Design**: All worker personae (Gateway, Processor, Archiver) are stateless, allowing for infinite expansion across a distributed mesh.

---

**Submission Status:** v3 (Orchestrated Microservice Mesh)
**Time Invested:** ~4 Hours of high-density iteration.

### 3. Decisions & Trade-Offs
- **Logical Isolation vs. Multi-DB:** We chose **Database-per-Tenant** (`tenant_<id>`). This offers the best security-to-overhead ratio for SaaS, allowing for per-tenant backups and schema migrations.
- **Async Processing:** We moved Lineage/AI tasks to an background worker pool. This ensures the Gateway remains responsive even during complex AST parsing of 1,000+ line queries.

---

## 🚀 Getting Started

### 1. Infrastructure (Docker)
```bash
docker-compose up -d
# Services: Postgres (storage), Redis (queue), MinIO (archive), Elasticsearch (metrics)
```

### 2. Service Boot
```bash
# 1. Install deps
python3 -m pip install -r requirements.txt

# 2. Start the Gateway (API)
PYTHONPATH=. python3 -m uvicorn gateway.main:app --port 8000 &

# 3. Start the Async Worker
PYTHONPATH=. python3 -m workers.worker &
```

### 3. End-to-End Test
```bash
python3 exporters/demo_exporter.py
# This script: Registers -> Syncs DDL -> Pushes Telemetry -> Triggers AI
```

---

## 🧠 AI Integration & Strategy
- **Strategy:** Our AI Optimization tier is decoupled via a "Status: PENDING" state in Postgres. This allows us to use expensive LLMs (OpenAI/Claude) without blocking ingest.
- **Safety:** We use **Idempotency Hashing** (`SHA256(text + dialect + schema)`) to ensure we only pay for AI analysis ONCE per unique query per schema version.
- **Vision:** Post-v2, the AI service would identify "Duplicate Query Signatures" and automatically suggest materialized views.

## 🛠️ Debugging & Observability
- **Structured Logs:** All workers output JSON logs to `/tmp/worker.log`. 
- **Global Error Handling:** The Gateway uses a custom middleware to suppress internal tracebacks, returning a `u-request-id` header for log correlation.
- **Retry Mechanism:** Failed jobs are moved to the RQ `failed` registry for manual or automated re-queuing.



---
**Author:** [Ashutosh]