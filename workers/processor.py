import hashlib
from sqlmodel import select
from core.db_manager import DatabaseManager
from core.models import Query, QueryMetric, CachedAsset
from workers.lineage import process_lineage
from workers.ai_optimization import process_ai_suggestions

class QueryProcessor:
    @staticmethod
    def handle_telemetry(tenant_id: str, data: dict, background_tasks=None):
        """Processes query execution metrics and deduplicates queries."""
        with DatabaseManager.get_session(tenant_id) as session:
            for sample in data.get("samples", []):
                # 1. Deduplicate via Hash
                q_text = sample["query_text"]
                q_hash = hashlib.sha256(q_text.encode()).hexdigest()
                
                # 2. Upsert Query
                existing_q = session.get(Query, q_hash)
                if not existing_q:
                    new_q = Query(
                        query_hash=q_hash,
                        db_alias=data["db_alias"],
                        query_text=q_text,
                        schema_version_analyzed=1, # Versioning logic could go here
                        dialect=data["dialect"]
                    )
                    session.add(new_q)
                    session.commit()
                    
                    # 3. Trigger Enrichment Workers
                    if background_tasks:
                        background_tasks.add_task(process_lineage, tenant_id, q_hash, q_text, data["dialect"])
                        background_tasks.add_task(process_ai_suggestions, tenant_id, q_hash, q_text)
                
                # 4. Insert Metric (Postgres for metadata/recent metrics)
                metric = QueryMetric(
                    query_hash=q_hash,
                    calls=sample["calls_delta"],
                    total_exec_time_ms=sample["total_exec_time_ms_delta"]
                )
                session.add(metric)
                
                # 5. HIGH-VOLUME SCALE: Ingest to Elasticsearch for Timeseries Aggregation
                # In v1+, we send raw execution events to ES to handle 2-3M queries / day.
                # ES allows sub-second aggregations over millions of rows.
                cls._ingest_to_elasticsearch(tenant_id, q_hash, sample)

            session.commit()

    @classmethod
    def _ingest_to_elasticsearch(cls, tenant_id: str, q_hash: str, sample: dict):
        """Mock Elasticsearch ingestion for timeseries metrics."""
        # In production, this would use the `elasticsearch` python client.
        # index = f"metrics-{tenant_id}"
        pass

    @classmethod
    def handle_assets(cls, tenant_id: str, data: dict):
        """Processes structural metadata updates."""
        with DatabaseManager.get_session(tenant_id) as session:
            for asset in data.get("data_assets", []):
                new_asset = CachedAsset(
                    db_alias=data["db_alias"],
                    asset_name=asset["asset_name"],
                    asset_type=asset["asset_type"],
                    schema_ddl=asset["schema_ddl"],
                    schema_version=asset["schema_version"]
                )
                session.add(new_asset)
            session.commit()
