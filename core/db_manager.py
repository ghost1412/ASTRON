import os
import threading
from typing import Dict
from sqlmodel import SQLModel, create_engine, Session, text
from sqlalchemy.exc import OperationalError

_db_lock = threading.Lock()

# Central config for Postgres
PG_BASE_URL = os.getenv("DATABASE_URL", "postgresql://admin:password@localhost:5432")
USE_SQLITE = os.getenv("USE_SQLITE", "false").lower() == "true"

class DatabaseManager:
    _engines: Dict[str, any] = {}

    @classmethod
    def create_tenant_db(cls, tenant_id: str):
        """Create a new logical database for a tenant. Decentralized model."""
        if USE_SQLITE:
            # For SQLite, the file is created automatically on engine connect.
            return
        
        # Connect to default 'postgres' database to execute CREATE DATABASE
        admin_url = f"{PG_BASE_URL}/postgres"
        engine = create_engine(admin_url, isolation_level="AUTOCOMMIT")
        
        db_name = f"tenant_{tenant_id}"
        with engine.connect() as conn:
            try:
                conn.execute(text(f'CREATE DATABASE "{db_name}"'))
                print(f"Created decentralized database: {db_name}")
            except Exception as e:
                print(f"Database {db_name} might already exist: {e}")
        engine.dispose()

    @classmethod
    def get_engine(cls, tenant_id: str):
        with _db_lock:
            if tenant_id not in cls._engines:
                if USE_SQLITE:
                    db_url = f"sqlite:///tenant_{tenant_id}.db"
                else:
                    db_url = f"{PG_BASE_URL}/tenant_{tenant_id}"
                
                engine = create_engine(db_url)
                from core.models import TenantMetadata, CachedAsset, Query, QueryMetric, LineageColumn, QuerySuggestion
                # Auto-initialize only the tenant-specific tables
                TenantMetadata.__table__.create(engine, checkfirst=True)
                CachedAsset.__table__.create(engine, checkfirst=True)
                Query.__table__.create(engine, checkfirst=True)
                QueryMetric.__table__.create(engine, checkfirst=True)
                LineageColumn.__table__.create(engine, checkfirst=True)
                QuerySuggestion.__table__.create(engine, checkfirst=True)
                cls._engines[tenant_id] = engine
                
        return cls._engines[tenant_id]

    @classmethod
    def get_session(cls, tenant_id: str):
        engine = cls.get_engine(tenant_id)
        return Session(engine)

def get_tenant_db(tenant_id: str):
    """Dependency to get a tenant-specific database session."""
    with DatabaseManager.get_session(tenant_id) as session:
        yield session
