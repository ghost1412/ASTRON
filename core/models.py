from datetime import datetime
from typing import List, Optional, Dict
from uuid import UUID, uuid4
from sqlmodel import SQLModel, Field, Relationship, JSON, Column
from sqlmodel import SQLModel, Field, Relationship, JSON, Column, UniqueConstraint

class TenantMetadata(SQLModel, table=True):
    __tablename__ = "tenant_metadata"
    company_id: str = Field(primary_key=True)
    company_name: str
    api_token: str
    admin_email: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class CachedAsset(SQLModel, table=True):
    __tablename__ = "cached_assets"
    __table_args__ = (
        UniqueConstraint("db_alias", "asset_name", "schema_version", name="unique_asset_version"),
    )
    id: Optional[int] = Field(default=None, primary_key=True)
    db_alias: str
    asset_name: str
    asset_type: str  # 'TABLE', 'VIEW', 'MATERIALIZED_VIEW'
    schema_ddl: str
    schema_version: int
    last_synced_at: datetime = Field(default_factory=datetime.utcnow)

class Query(SQLModel, table=True):
    __tablename__ = "queries"
    query_hash: str = Field(primary_key=True)  # hash(query_text + dialect + schema_version)
    db_alias: str
    user_id: Optional[str] = Field(default=None, index=True)
    query_text: str
    schema_version_analyzed: int
    dialect: str
    first_seen_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    last_seen_at: datetime = Field(default_factory=datetime.utcnow)


class QueryMetric(SQLModel, table=True):
    __tablename__ = "query_metrics"
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    query_hash: str = Field(foreign_key="queries.query_hash")
    calls: int
    total_exec_time_ms: int
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class LineageColumn(SQLModel, table=True):
    __tablename__ = "lineage_columns"
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    query_hash: str = Field(foreign_key="queries.query_hash")
    asset_name: str
    column_name: str
    clause_type: str  # SELECT, WHERE, JOIN, etc.

class QuerySuggestion(SQLModel, table=True):
    __tablename__ = "query_suggestions"
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    query_hash: str = Field(foreign_key="queries.query_hash", unique=True)
    status: str  # PENDING, DONE, FAILED
    suggestions: Dict = Field(default_factory=dict, sa_column=Column(JSON))
    error: Optional[str] = None
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class NetworkThreat(SQLModel, table=True):
    __tablename__ = "network_threats"
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    timestamp: datetime = Field(default_factory=datetime.utcnow, index=True)
    source_ip: str
    dest_ip: str
    protocol: str
    port: int
    threat_type: str  # 'MALWARE', 'ANOMALY', 'PORT_SCAN'
    risk_score: float  # 0.0 to 1.0
    summary: str
    is_active: bool = Field(default=True)

