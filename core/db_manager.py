import os
import threading
import structlog
from typing import Dict
from sqlmodel import SQLModel, create_engine, Session, text

logger = structlog.get_logger()
_db_lock = threading.Lock()

# Central config for Postgres
PG_BASE_URL = os.getenv("DATABASE_URL")
if not PG_BASE_URL:
    raise ValueError("DATABASE_URL environment variable is NOT set. Please copy .env.example to .env and configure your secrets.")

USE_SQLITE = os.getenv("USE_SQLITE", "false").lower() == "true"

class DatabaseManager:
    _engines: Dict[str, any] = {}

    @classmethod
    def create_tenant_db(cls, tenant_id: str):
        """Create a new logical database for a tenant. Decentralized model."""
        if USE_SQLITE:
            return
        
        # Connect to default 'postgres' database to execute CREATE DATABASE
        admin_url = f"{PG_BASE_URL}/postgres"
        engine = create_engine(admin_url, isolation_level="AUTOCOMMIT")
        
        db_name = f"tenant_{tenant_id}"
        with engine.connect() as conn:
            try:
                conn.execute(text(f'CREATE DATABASE "{db_name}"'))
                logger.info("database_created", db_name=db_name)
            except Exception as e:
                logger.debug("database_already_exists", db_name=db_name)
        engine.dispose()

    @classmethod
    def get_engine(cls, tenant_id: str):
        """Retrieves or creates a SQLAlchemy engine for a specific tenant."""
        with _db_lock:
            if tenant_id not in cls._engines:
                if USE_SQLITE:
                    db_url = f"sqlite:///tenant_{tenant_id}.db"
                else:
                    db_url = f"{PG_BASE_URL}/tenant_{tenant_id}"
                
                engine = create_engine(db_url, pool_pre_ping=True)
                
                # v4.4: Deterministic Schema Persistence
                # Import all models to ensure they are registered in SQLModel.metadata
                from core.models import TenantMetadata, CachedAsset, Query, QueryMetric, LineageColumn, QuerySuggestion
                
                # Unified Schema Synchronization logic
                try:
                    SQLModel.metadata.create_all(engine)
                    logger.info("schema_initialized", tenant_id=tenant_id)
                except Exception as e:
                    logger.error("schema_initialization_failed", tenant_id=tenant_id, error=str(e))
                
                cls._engines[tenant_id] = engine
                
        return cls._engines[tenant_id]

    @classmethod
    def get_session(cls, tenant_id: str):
        """Utility to get a thread-safe Session for a specific tenant."""
        engine = cls.get_engine(tenant_id)
        return Session(engine)

def get_tenant_db(tenant_id: str):
    """Dependency for FastAPI to inject a tenant-specific database session."""
    with DatabaseManager.get_session(tenant_id) as session:
        yield session
