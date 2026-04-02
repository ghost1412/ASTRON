import os
from typing import Dict
from sqlmodel import SQLModel, create_engine, Session, text
from sqlalchemy.exc import OperationalError

# Master database stores tenant information
MASTER_DB_URL = os.getenv("DATABASE_URL", "postgresql://admin:password@localhost:5432/query_intel_master")
USE_SQLITE = os.getenv("USE_SQLITE", "false").lower() == "true"

class DatabaseManager:
    _engines: Dict[str, any] = {}
    _master_engine = None

    @classmethod
    def initialize_master(cls):
        global USE_SQLITE
        if cls._master_engine:
            return
        
        if not USE_SQLITE:
            try:
                cls._master_engine = create_engine(MASTER_DB_URL)
                # Test connection
                with cls._master_engine.connect() as conn:
                    conn.execute(text("SELECT 1"))
            except Exception:
                print("Postgres connection failed. Falling back to SQLite for demo purposes.")
                USE_SQLITE = True
        
        if USE_SQLITE:
            cls._master_engine = create_engine("sqlite:///master.db")
            from core.models import Tenant
            SQLModel.metadata.create_all(cls._master_engine)

    @classmethod
    def get_master_session(cls):
        cls.initialize_master()
        return Session(cls._master_engine)

    @classmethod
    def create_tenant_db(cls, tenant_id: str):
        """Create a new logical database for a tenant."""
        cls.initialize_master()
        if USE_SQLITE:
            # SQLite handles database creation via file paths, nothing to do here
            return
        
        with cls._master_engine.connect() as conn:
            conn.execute(text("COMMIT"))
            try:
                conn.execute(text(f'CREATE DATABASE "tenant_{tenant_id}"'))
            except Exception as e:
                print(f"Database tenant_{tenant_id} might already exist: {e}")

    @classmethod
    def get_engine(cls, tenant_id: str):
        cls.initialize_master()
        if tenant_id not in cls._engines:
            if USE_SQLITE:
                db_url = f"sqlite:///tenant_{tenant_id}.db"
            else:
                db_url = f"postgresql://admin:password@localhost:5432/tenant_{tenant_id}"
            
            engine = create_engine(db_url)
            from core.models import CachedAsset, Query, QueryMetric, LineageColumn, QuerySuggestion
            SQLModel.metadata.create_all(engine)
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
