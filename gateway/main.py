from fastapi import FastAPI, Depends, HTTPException, Security, BackgroundTasks
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlmodel import select, Session
from core.db_manager import DatabaseManager
from core.models import Tenant, Query, QueryMetric, CachedAsset, LineageColumn, QuerySuggestion
from gateway.onboarding import router as onboarding_router
from workers.lineage import process_lineage
from workers.ai_optimization import process_ai_suggestions
from workers.processor import QueryProcessor
from typing import List, Optional

app = FastAPI(title="Query Intelligence Platform Gateway")
app.include_router(onboarding_router)

security = HTTPBearer()

def get_current_tenant(auth: HTTPAuthorizationCredentials = Security(security)):
    """Validates the API token and returns the tenant_id."""
    token = auth.credentials
    with DatabaseManager.get_master_session() as session:
        statement = select(Tenant).where(Tenant.api_token == token)
        tenant = session.exec(statement).first()
        if not tenant:
            raise HTTPException(status_code=401, detail="Invalid API Token")
        return tenant.id

@app.get("/v1/queries")
def list_queries(tenant_id: str = Depends(get_current_tenant)):
    """List aggregated metrics for the tenant's queries."""
    with DatabaseManager.get_session(tenant_id) as session:
        queries = session.exec(select(Query)).all()
        return {"data": [q.dict() for q in queries]}

@app.get("/v1/queries/{query_hash}")
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
            if "suggestions" in includes:
                suggestions = session.exec(select(QuerySuggestion).where(QuerySuggestion.query_hash == query_hash)).first()
                result["suggestions"] = suggestions.dict() if suggestions else None
                
        return result

@app.post("/v1/telemetry/assets")
def push_assets(
    assets_data: dict, 
    background_tasks: BackgroundTasks,
    tenant_id: str = Depends(get_current_tenant)
):
    """Ingest structural metadata via the Query Processor."""
    background_tasks.add_task(QueryProcessor.handle_assets, tenant_id, assets_data)
    return {"status": "accepted"}

@app.post("/v1/telemetry/queries/bulk")
def push_queries(
    telemetry_data: dict,
    background_tasks: BackgroundTasks,
    tenant_id: str = Depends(get_current_tenant)
):
    """Ingest query metrics via the Query Processor."""
    background_tasks.add_task(QueryProcessor.handle_telemetry, tenant_id, telemetry_data, background_tasks)
    return {"status": "accepted"}
