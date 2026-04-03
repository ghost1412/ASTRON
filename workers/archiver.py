import os
from datetime import datetime, timedelta
from sqlmodel import Session, select, delete
from core.db_manager import DatabaseManager
from core.models import Query, QueryMetric
from core.storage_manager import StorageManager
import structlog

logger = structlog.get_logger(__name__)

class DataLifecycleManager:
    """
    Implements 30-day archival logic (Hot -> Cold).
    Optimized for high-volume telemetry offloading with low Postgres overhead.
    """
    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        self.db = DatabaseManager()
        self.storage = StorageManager()
        self.threshold = datetime.utcnow() - timedelta(days=30)

    def archive_hot_telemetry(self):
        """
        Moves Query Metrics older than 30 days to Cold Storage.
        Uses Batch-and-Purge to minimize Postgres load.
        """
        logger.info("telemetry_archival_started", tenant=self.tenant_id, threshold=self.threshold)
        
        with self.db.get_session(self.tenant_id) as session:
            # 1. Identify older metrics
            # Only fetch necessary columns for Parquet archival
            query = select(QueryMetric).where(QueryMetric.timestamp < self.threshold).limit(10000)
            stale_metrics = session.exec(query).all()
            
            if not stale_metrics:
                logger.info("archival_skipped_no_data", tenant=self.tenant_id)
                return

            # 2. Convert to list for StorageManager
            data_to_archive = [m.model_dump() for m in stale_metrics]
            
            # 3. Upload to Cold Storage (MinIO)
            # Path: {tenant}/telemetry/{year}/{month}/...
            s3_key = self.storage.archive_to_parquet(self.tenant_id, data_to_archive, "telemetry")
            
            if s3_key:
                # 4. Atomic Purge: Delete only verified archived records
                # Use Bulk DELETE for performance
                metric_ids = [m.id for m in stale_metrics]
                delete_stmt = delete(QueryMetric).where(QueryMetric.id.in_(metric_ids))
                session.exec(delete_stmt)
                session.commit()
                
                logger.info("hot_purge_complete", tenant=self.tenant_id, count=len(metric_ids))

    def archive_inactive_queries(self):
        """
        Moves Query Definitions inactive for > 30 days to Cold Storage.
        """
        with self.db.get_session(self.tenant_id) as session:
            # Only archive if last_seen was > 30 days ago
            query = select(Query).where(Query.last_seen < self.threshold).limit(5000)
            stale_queries = session.exec(query).all()
            
            if stale_queries:
                data = [q.model_dump() for q in stale_queries]
                s3_key = self.storage.archive_to_parquet(self.tenant_id, data, "queries")
                
                if s3_key:
                    q_hashes = [q.query_hash for q in stale_queries]
                    delete_stmt = delete(Query).where(Query.query_hash.in_(q_hashes))
                    session.exec(delete_stmt)
                    session.commit()
                    logger.info("inactive_query_purge_complete", tenant=self.tenant_id, count=len(q_hashes))

if __name__ == "__main__":
    # In a microservice mesh, the persona is defined by the environment
    active_tenant = os.getenv("ACTIVE_TENANT", "test-company-1")
    logger.info("lifecycle_manager_persona_started", tenant=active_tenant)
    
    dlm = DataLifecycleManager(active_tenant)
    dlm.archive_hot_telemetry()
    dlm.archive_inactive_queries()
