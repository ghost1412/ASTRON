from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import select

from core.db_manager import DatabaseManager
from core.models import Query, LineageColumn, QuerySuggestion, CachedAsset
from gateway.deps import get_current_tenant, get_tenant_queue
from workers.processor import QueryProcessor

router = APIRouter(tags=["telemetry"])

# Threshold for job chunking to prevent "Monolithic Blockage" (Fair-Share)
CHUNK_SIZE = 5000

@router.post("/assets")
def ingest_assets(data: dict, tenant_id: str = Depends(get_current_tenant)):
    """Ingest database structural metadata (DDL)."""
    QueryProcessor.handle_assets(tenant_id, data)
    return {"status": "success", "message": f"Processed {len(data.get('data_assets', []))} assets"}

@router.get("/assets")
def list_assets(tenant_id: str = Depends(get_current_tenant)):
    """List structural metadata from the Asset Catalog."""
    with DatabaseManager().get_session(tenant_id) as session:
        assets = session.exec(select(CachedAsset)).all()
        return {"data": assets}

@router.get("/queries")
def list_queries(
    dialect: Optional[str] = None,
    db_alias: Optional[str] = None,
    user_id: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    limit: int = 50,
    offset: int = 0,
    tenant_id: str = Depends(get_current_tenant)
):
    """List detected queries with pagination and sorted order."""
    with DatabaseManager.get_session(tenant_id) as session:
        statement = select(Query).order_by(Query.first_seen_at.desc()).offset(offset).limit(limit)
        if dialect:
            statement = statement.where(Query.dialect == dialect)
        if db_alias:
            statement = statement.where(Query.db_alias == db_alias)
        if user_id:
            statement = statement.where(Query.user_id == user_id)
        if date_from:
            statement = statement.where(Query.first_seen_at >= date_from)
        if date_to:
            statement = statement.where(Query.first_seen_at <= date_to)
            
        queries = session.exec(statement).all()
        return {"data": queries}


@router.get("/queries/{query_hash}")
def get_query_details(
    query_hash: str, 
    include: Optional[str] = None,
    tenant_id: str = Depends(get_current_tenant)
):
    """Fetch exhaustive details for a specific query."""
    with DatabaseManager.get_session(tenant_id) as session:
        query = session.get(Query, query_hash)
        if not query:
            raise HTTPException(status_code=404, detail="Query not found")
        
        result = query.dict()
        if include:
            includes = include.split(",")
            if "lineage" in includes:
                lineage = session.exec(select(LineageColumn).where(LineageColumn.query_hash == query_hash)).all()
                result["lineage"] = [l.dict() for l in lineage]
                
                # Synthesis for Visual Observability: Generate Mermaid.js graph string
                # Format: graph LR; TableA --> Column1; TableA --> Column2;
                mermaid_lines = ["graph LR"]
                for l in lineage:
                    mermaid_lines.append(f"  {l.asset_name} --> {l.column_name}")
                result["mermaid_lineage"] = "\n".join(mermaid_lines)
                
            if "suggestions" in includes:
                suggestions = session.exec(select(QuerySuggestion).where(QuerySuggestion.query_hash == query_hash)).first()
                result["suggestions"] = suggestions.dict() if suggestions else None
        return result


@router.post("/telemetry/assets")
def push_assets(
    assets_data: dict, 
    tenant_id: str = Depends(get_current_tenant)
):
    """Ingest structural metadata. Dispatched to the sharded priority queue."""
    q = get_tenant_queue(tenant_id)
    q.enqueue(QueryProcessor.handle_assets, tenant_id, assets_data)
    return {"status": "accepted", "job_id": "queued", "shard": q.name}

@router.post("/telemetry/queries/bulk")
def push_queries(
    telemetry_data: dict,
    tenant_id: str = Depends(get_current_tenant)
):
    """Ingest query metrics with Fair-Share Chunking."""
    q = get_tenant_queue(tenant_id)
    
    samples = telemetry_data.get("samples", [])
    if len(samples) > CHUNK_SIZE:
        # 1. Fair-Share Chunking: Break massive ingests into interleaved tasks
        # This prevents a single 3M query ingest from blocking a shard lane for hours.
        for i in range(0, len(samples), CHUNK_SIZE):
            chunk = samples[i : i + CHUNK_SIZE]
            payload_chunk = {**telemetry_data, "samples": chunk}
            q.enqueue(QueryProcessor.handle_telemetry, tenant_id, payload_chunk)
    else:
        # 2. Standard Dispatch
        q.enqueue(QueryProcessor.handle_telemetry, tenant_id, telemetry_data)
        
    return {"status": "accepted", "job_id": "queued", "shard": q.name}
