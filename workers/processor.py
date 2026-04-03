import hashlib
import os
import structlog
from datetime import datetime
from sqlmodel import select
from redis import Redis
from rq import Queue
from core.db_manager import DatabaseManager
from core.models import Query, QueryMetric, CachedAsset
from workers.lineage import process_lineage
from workers.ai_optimization import process_ai_suggestions

# Setup structured logging
logger = structlog.get_logger()

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
ES_HOST = os.getenv("ELASTICSEARCH_URL", "http://elasticsearch:9200")
import httpx

redis_conn = Redis(host=REDIS_HOST, port=6379)
task_queue = Queue("default", connection=redis_conn)

class QueryProcessor:
    @classmethod
    def handle_telemetry(cls, tenant_id: str, data: dict):
        """Processes query execution metrics and deduplicates queries."""
        log = logger.bind(tenant_id=tenant_id, db_alias=data.get("db_alias"))
        log.info("processing_telemetry_batch", sample_count=len(data.get("samples", [])))

        with DatabaseManager.get_session(tenant_id) as session:
            for sample in data.get("samples", []):
                q_text = sample["query_text"]
                dialect = data.get("dialect", "postgres")
                schema_ver = data.get("schema_version", 1)
                
                # Salt the hash with dialect and schema version
                # This ensures that if the schema evolves, we re-trigger analysis
                hash_input = f"{q_text}:{dialect}:{schema_ver}"
                q_hash = hashlib.sha256(hash_input.encode()).hexdigest()
                
                # 1. Deduplicate via Salted Hash
                existing_q = session.get(Query, q_hash)
                if not existing_q:
                    log.info("new_query_version_detected", query_hash=q_hash, schema_ver=schema_ver)
                    new_q = Query(
                        query_hash=q_hash,
                        db_alias=data["db_alias"],
                        query_text=q_text,
                        schema_version_analyzed=schema_ver,
                        dialect=dialect
                    )
                    session.add(new_q)
                    session.commit()
                    
                    # 2. Trigger Enrichment Workers via Distributed Queue (RQ)
                    # We don't pass the queue reference anymore to avoid pickling errors.
                    # The worker will import its own connection.
                    task_queue.enqueue(process_lineage, tenant_id, q_hash, q_text, data["dialect"])
                    task_queue.enqueue(process_ai_suggestions, tenant_id, q_hash, q_text)
                
                # 3. DB Insertion (Postgres) - Metadata & Basic Metrics
                metric = QueryMetric(
                    query_hash=q_hash,
                    calls=sample["calls_delta"],
                    total_exec_time_ms=sample["total_exec_time_ms_delta"]
                )
                session.add(metric)
                
                # 4. High-Volume Ingest (Elasticsearch) - Timeseries Aggregations
                # ES handles 2-3M events/day for sub-second dashboards
                cls._ingest_to_elasticsearch(tenant_id, q_hash, sample, data["db_alias"])

            session.commit()
            log.info("telemetry_batch_committed")

    @classmethod
    def _ingest_to_elasticsearch(cls, tenant_id: str, q_hash: str, sample: dict, db_alias: str):
        """Real Elasticsearch ingestion for high-volume timeseries metrics."""
        index_name = f"metrics-{tenant_id}"
        doc = {
            "query_hash": q_hash,
            "db_alias": db_alias,
            "calls": sample["calls_delta"],
            "exec_time_ms": sample["total_exec_time_ms_delta"],
            "timestamp": sample.get("timestamp", datetime.utcnow().isoformat())
        }
        try:
            res = httpx.post(f"{ES_HOST}/{index_name}/_doc", json=doc)
            res.raise_for_status()
        except Exception as e:
            logger.error("es_ingest_failed", error=str(e), query_hash=q_hash)

    @classmethod
    def handle_assets(cls, tenant_id: str, data: dict):
        """Processes structural metadata updates with Upsert (Idempotency) logic."""
        logger.info("ingesting_assets", tenant_id=tenant_id, asset_count=len(data.get("data_assets", [])))
        db_alias = data["db_alias"]
        with DatabaseManager.get_session(tenant_id) as session:
            for asset in data.get("data_assets", []):
                asset_name = asset["asset_name"]
                ver = asset["schema_version"]
                
                # Check for existing version to prevent duplication
                stmt = select(CachedAsset).where(
                    CachedAsset.db_alias == db_alias,
                    CachedAsset.asset_name == asset_name,
                    CachedAsset.schema_version == ver
                )
                existing = session.exec(stmt).first()
                if existing:
                    existing.last_synced_at = datetime.utcnow()
                    session.add(existing)
                else:
                    new_asset = CachedAsset(
                        db_alias=db_alias,
                        asset_name=asset_name,
                        asset_type=asset["asset_type"],
                        schema_ddl=asset["schema_ddl"],
                        schema_version=ver
                    )
                    session.add(new_asset)
            session.commit()
