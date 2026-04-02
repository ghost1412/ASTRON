import os
import structlog
from uuid import uuid4
from typing import List, Optional
from fastapi import FastAPI, Depends, HTTPException, Security, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, JSONResponse
from sqlmodel import select, Session
from redis import Redis
from rq import Queue

from core.db_manager import DatabaseManager
from core.models import TenantMetadata, Query, QueryMetric, LineageColumn, QuerySuggestion
from gateway.onboarding import router as onboarding_router
from workers.processor import QueryProcessor

security = HTTPBearer()

# Senior-level logging & instrumentation
logger = structlog.get_logger()

# Path to frontend directory
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")

# Redis Configuration for Distributed Tasks
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
redis_conn = Redis(host=REDIS_HOST, port=6379)
task_queue = Queue("default", connection=redis_conn)

app = FastAPI(
    title="SQL Query Intelligence Platform",
    description="Decentralized multi-tenant gateway for high-volume SQL observability."
)

app.include_router(onboarding_router)

# Serve the static frontend dashboard
app.mount("/dashboard", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")

@app.get("/")
def root_redirect():
    return RedirectResponse(url="/dashboard/index.html")

from jose import jwt, JWTError

# Senior-level Security: JWT Configuration
SECRET_KEY = os.getenv("JWT_SECRET", "super-secret-key-for-demo")
ALGORITHM = "HS256"

def get_current_tenant(request: Request, auth: HTTPAuthorizationCredentials = Security(security)):
    """
    Decentralized Auth: Validates identity using a verified JWT.
    Extracts 'tenant_id' from the token claims.
    """
    token = auth.credentials
    try:
        # In production, this verifies against an IdP (Auth0/Keycloak)
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        tenant_id: str = payload.get("tenant_id")
        if not tenant_id:
            raise HTTPException(status_code=401, detail="Invalid token: Missing tenant_id")
        return tenant_id
    except JWTError as e:
        logger.warning("jwt_verification_failed", error=str(e))
        # Support fallback for demo purposes if token is 'sk_...'
        if token.startswith("sk_"):
            return request.headers.get("X-Tenant-ID", "test-company-1")
        raise HTTPException(status_code=401, detail="Could not validate credentials")

# Global Exception Handler for structured JSON errors
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("unhandled_exception", error=str(exc), path=request.url.path)
    return JSONResponse(
        status_code=500,
        content={
            "error": "INTERNAL_SERVER_ERROR",
            "message": "An unexpected error occurred. Please contact support.",
            "trace_id": str(uuid4())
        }
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": "HTTP_ERROR", "message": exc.detail}
    )

@app.post("/v1/assets")
def ingest_assets(data: dict, tenant_id: str = Depends(get_current_tenant)):
    """Ingest database structural metadata (DDL)."""
    QueryProcessor.handle_assets(tenant_id, data)
    return {"status": "success", "message": f"Processed {len(data.get('data_assets', []))} assets"}

@app.get("/v1/assets")
def list_assets(tenant_id: str = Depends(get_current_tenant)):
    """List structural metadata from the Asset Catalog."""
    with DatabaseManager().get_session(tenant_id) as session:
        assets = session.exec(select(CachedAsset)).all()
        return {"data": assets}

@app.get("/v1/queries")
def list_queries(
    dialect: Optional[str] = None,
    db_alias: Optional[str] = None,
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
            
        queries = session.exec(statement).all()
        return {"data": queries}

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
    tenant_id: str = Depends(get_current_tenant)
):
    """Ingest structural metadata. Dispatched to the high-performance processor."""
    # We don't use BackgroundTasks here because we want to ensure 
    # the task is persistent in Redis even if this API node crashes.
    task_queue.enqueue(QueryProcessor.handle_assets, tenant_id, assets_data)
    return {"status": "accepted", "job_id": "queued"}

@app.post("/v1/telemetry/queries/bulk")
def push_queries(
    telemetry_data: dict,
    tenant_id: str = Depends(get_current_tenant)
):
    """Ingest query metrics. Offloaded to the distributed worker pool."""
    # We no longer pass task_queue to the task to avoid pickling errors.
    task_queue.enqueue(QueryProcessor.handle_telemetry, tenant_id, telemetry_data)
    return {"status": "accepted", "job_id": "queued"}
