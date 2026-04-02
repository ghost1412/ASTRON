import os
import sys
from datetime import datetime, timedelta
from sqlmodel import Session, select, func
from core.db_manager import DatabaseManager
from core.models import QueryMetric, Query
from workers.archiver import DataLifecycleManager
import time
import uuid

def seed_stale_data(tenant_id: str, count: int = 1000):
    """Injects data with timestamps older than 30 days."""
    db = DatabaseManager()
    stale_date = datetime.utcnow() - timedelta(days=31)
    
    with db.get_session(tenant_id) as session:
        print(f"🌱 Seeding {count} stale metrics for {tenant_id}...")
        
        # Create a dummy query to link to
        q = Query(
            query_hash=f"stale_{uuid.uuid4().hex[:8]}",
            query_text="SELECT * FROM archival_test",
            db_alias="prod_cluster_01",
            schema_version_analyzed=1,
            dialect="postgres",
            first_seen_at=stale_date,
            last_seen_at=stale_date
        )
        session.add(q)
        session.commit()

        for i in range(count):
            m = QueryMetric(
                query_hash=q.query_hash,
                timestamp=stale_date,
                calls=1,
                total_exec_time_ms=100.0
            )
            session.add(m)
            if i % 1000 == 0:
                session.commit()
        session.commit()

def run_stress_archive(tenant_id: str):
    dlm = DataLifecycleManager(tenant_id)
    
    print(f"🚀 Triggering 30-Day Archival Stress Test...")
    start = time.perf_counter()
    
    # Run the hot telemetry archival
    dlm.archive_hot_telemetry()
    dlm.archive_inactive_queries()
    
    duration = time.perf_counter() - start
    print(f"✅ Archival Complete in {duration:.2f}s")

if __name__ == "__main__":
    tenant = "acme-corp"
    seed_stale_data(tenant, 5000) # Inject 5k stale records
    run_stress_archive(tenant)
