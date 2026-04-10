# ASTRON | SQL Query Intelligence Platform

> [!NOTE]
> **Project Status: WIP (Pet Project)**
> ASTRON is an active experimental project focused on high-performance SQL observability and sidecar security architectures. While the core telemetry mesh is operational, features like "Active Mitigation" and "Auto-Scaling" are currently under development.

---

## 🚀 Evaluator QuickStart (3 Minutes)

1.  **Stop Local Services**: Ensure no local Postgres (5432) or Redis (6379) are running on your host.
2.  **Boot the Mesh**: 

## 🖼️ Interface Highlights

### 1. Neural Sentry Hub (Security Ops)
The Sentry Hub provides a real-time view of all network traffic, including an interactive Mermaid-driven traffic map and the forensic threat registry.
![Neural Sentry Dashboard](./assets/dashboard_sentry.png)

### 2. Neural Monitor (Performance Ops)
Track global query metrics, deduplicated hashes, and provisioned instance health across your entire decentralized infrastructure.
![Neural Monitor Dashboard](./assets/dashboard_monitor.png)

### 3. Discovery Hub (Lineage & Optimization)
Drill down into specific queries to visualize SQL lineage, identify optimization paths, and analyze shard integrity.
![Discovery Hub Modal](./assets/discovery_hub.png)

---
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
A high-volume telemetry pipeline for SQL query observability, lineage extraction, and intelligent optimization. Persists comprehensive metadata (User ID, Dialect, Timestamps) with advanced multi-tenant filtering.

 10M+ queries per day using a distributed telemetry pipeline.

---

## 🏗️ Architectural Vision: Scaling to Enterprise

### 1. The Engineering Challenge
The platform addresses the complex requirement for a **Scalable Telemetry Pipeline** capable of parsing thousands of overlapping SQL ASTs (Abstract Syntax Trees) per minute. 
- **Core Principles:** 
    - Queries are high-frequency, low-latency events requiring decoupled ingestion architectures.
    - Lineage analysis is CPU-intensive and must be offloaded from the Gateway to asynchronous workers.
    - Tenancy requires strict logical isolation (Database-per-Tenant) to satisfy enterprise security and compliance audits.

### 2. Incremental Evolution
- **v0 (Development):** Monolithic engine. Local recursive AST parsing.
- **v1 (Operational):** Transition to **PostgreSQL** for strict multi-tenancy. Decentralized metadata management via Tenant ID.
- **v2 (Scalable):** Distributed Task Queue using **Redis (RQ)**. Asynchronous Lineage mapping and Deterministic Query Optimization. **Elasticsearch** timeseries scaling for 2M+ metric aggregation.
- **v3 (Enterprise):** Containerized microservice mesh for high availability. Auto-archiving telemetry pipelines (Data Lifecycle Management).## Architecture (Microservice Mesh)
- **Inbound Telemetry**: Decoupled from core processing. Gateway accepts telemetry and places it on **Redis (RQ)**.
- **worker-analysis**: A standalone microservice that consumes the queue for Lineage and Optimization logic.
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


## 🧩 Core Decisions & Trade-Offs
- **Logical Isolation vs. Multi-DB:** We chose **Database-per-Tenant** (`tenant_<id>`). This offers the best security-to-overhead ratio for SaaS, allowing for per-tenant backups and schema migrations without deploying vast numbers of compute instances.
- **Async Processing:** We moved Lineage mapping and Optimization generation to a background worker pool (`analysis-worker`). This ensures the API Gateway remains sub-millisecond responsive even during complex AST parsing of massive, 1,000+ line queries.
- **The SQLGlot AST Engine:** We explicitly chose `sqlglot` for our parsing capability. Why? Because it is a pure Python library capable of interpreting over 20 different SQL dialects *without* requiring heavy database connections or C-dependencies. It allows our microservice to securely construct and traverse an Abstract Syntax Tree (AST) in memory to perform deep lineage column extraction.

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

## 🧠 Advanced Optimization Strategy
- **Strategy:** Our optimization tier is highly decoupled via a "Status: PENDING" state in the database. This allows us to integrate sophisticated algorithms or heuristic models in the `analysis-worker` without blocking the core data ingestion pipeline.
- **Safety:** We use **Idempotency Hashing** (`SHA256(text + dialect + schema)`) to ensure that we never redundantly process or charge computation cycles for identical queries unless the underlying database schema has evolved.
- **Vision:** Post-v2, the optimization service builds canonical "Query Signatures" to identify cluster bottlenecks and autonomously suggest materialized view architectures.

## 🛠️ Debugging & Observability
- **Structured Logs:** All workers output JSON logs to `/tmp/worker.log`. 
- **Global Error Handling:** The Gateway uses a custom middleware to suppress internal tracebacks, returning a `u-request-id` header for log correlation.
- **Retry Mechanism:** Failed jobs are moved to the RQ `failed` registry for manual or automated re-queuing.



## 🛡️ Security & Privacy (v7.0)
ASTRON is built with a **Privacy-First** architecture:
- **Masked Signatures**: Only redacted forensic signatures (e.g., `XXXX-XXXX-1234`) are stored in the central registry.
- **Passive Sniffing**: Zero-overhead network auditing that does not intercept application-level sensitive memory.
- **Strict Mode**: Enable `ASTRON_STRICT_MODE` for professional-grade checksum validation of PII.

## ⚖️ License
Licensed under the [Apache License 2.0](LICENSE).

---
**Author:** [Ashutosh]