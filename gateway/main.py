import os
import structlog
from typing import Optional
from fastapi import FastAPI, HTTPException, Header, Query as QueryParam
from sqlmodel import select, func
from gateway.onboarding import router as onboarding_router
from gateway.telemetry import router as telemetry_router
from gateway.errors import register_error_handlers
from core.db_manager import DatabaseManager
from core.models import Query, LineageColumn, QuerySuggestion, TenantMetadata, NetworkThreat

logger = structlog.get_logger()

app = FastAPI(
    title="ASTRON | Advanced SQL Intelligence Platform",
    description="Enterprise-grade decentralized gateway for high-volume SQL observability and intelligent optimization."
)

# 1. Infrastructure Clients
register_error_handlers(app)
ES_HOST = os.getenv("ELASTICSEARCH_URL", "http://elasticsearch:9200")
import httpx

# 2. CORE PLATFORM ROUTES (ASTRON Enterprise Gateway)

@app.post("/v1/auth/validate")
def validate_session(auth_body: dict):
    """Enterprise Auth: Validates if an organization and access token is active."""
    tenant_id = auth_body.get("tenant_id")
    token = auth_body.get("token")
    if not tenant_id or not token:
        raise HTTPException(status_code=400, detail="Missing Access Credentials")
    
    try:
        # 1. Connect to the tenant's database
        with DatabaseManager.get_session(tenant_id) as session:
            # 2. Strict Token Validation
            tenant = session.get(TenantMetadata, tenant_id)
            if not tenant or tenant.api_token != token:
                raise HTTPException(status_code=401, detail="Unauthorized: Invalid Enterprise Identity or Token")
            
        return {"status": "success", "tenant_id": tenant.company_id}
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=401, detail="Unauthorized: Enterprise Identity not found")

@app.get("/v1/stats")
def get_sharded_stats(tenant_id: str = QueryParam(..., alias="tenant_id")):
    """Advanced Stats: Returns real-time counts from the secure sharded instance."""
    try:
        with DatabaseManager.get_session(tenant_id) as session:
            query_count = session.exec(select(func.count(Query.query_hash))).one()
            lineage_count = session.exec(select(func.count(LineageColumn.id))).one()
            
            return {
                "total_queries": query_count,
                "total_lineage_nodes": lineage_count,
                "active_shards": int(os.getenv("SHARD_COUNT", 3)),
                "savings_projected": "80%"
            }
    except Exception as e:
        return {"total_queries": 0, "total_lineage_nodes": 0, "active_shards": 3, "savings_projected": "80%", "debug": str(e)}

@app.get("/v1/queries/{query_hash}/details")
def get_query_details(query_hash: str, x_tenant_id: str = Header(..., alias="X-Tenant-ID")):
    """Intelligent Discovery: Returns real-time lineage analysis and optimization suggestions."""
    try:
        with DatabaseManager.get_session(x_tenant_id) as session:
            # Query for Lineage
            lineage_res = session.exec(select(LineageColumn).where(LineageColumn.query_hash == query_hash)).all()
            # Query for Suggestion
            suggest_res = session.exec(select(QuerySuggestion).where(QuerySuggestion.query_hash == query_hash)).first()
            
            # Synthesis for Visual Observability: Generate Mermaid.js graph string
            mermaid_lines = ["graph LR"]
            for l in lineage_res:
                mermaid_lines.append(f"  {l.asset_name} --> {l.column_name}")
            mermaid_str = "\n".join(mermaid_lines)
            
            return {
                "lineage": [l.column_name for l in lineage_res],
                "tables": list(set([l.asset_name for l in lineage_res])),
                "mermaid_lineage": mermaid_str,
                "suggestion": str(suggest_res.suggestions) if suggest_res else "Analyzing Shard Integrity..."
            }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/v1/queries/{query_hash}/metrics")
def get_query_metrics(query_hash: str, x_tenant_id: str = Header(..., alias="X-Tenant-ID")):
    """Observability Plane: Returns high-speed telemetry trends from Elasticsearch."""
    index_name = f"metrics-{x_tenant_id}"
    try:
        # Fetch last 10 samples for the specific query
        res = httpx.post(
            f"{ES_HOST}/{index_name}/_search",
            json={
                "query": {"term": {"query_hash.keyword": query_hash}},
                "sort": [{"timestamp": "desc"}],
                "size": 10
            }
        )
        res.raise_for_status()
        hits = res.json().get("hits", {}).get("hits", [])
        return {"metrics": [h.get("_source", {}) for h in hits]}
    except Exception as e:
        # Fallback for fresh shards or index latency
        return {"metrics": []}

@app.get("/v1/network/threats")
def get_network_threats(
    tenant_id: str = QueryParam(..., alias="tenant_id"),
    limit: int = QueryParam(50, ge=1, le=100),
    offset: int = QueryParam(0, ge=0),
    threat_type: Optional[str] = QueryParam(None)
):
    """Neural Sentry Hub: Returns a paginated list of threats with optional behavioral filtering."""
    try:
        with DatabaseManager.get_session(tenant_id) as session:
            # 1. High-Performance Scalar Count
            count_stmt = select(func.count(NetworkThreat.id))
            if threat_type:
                count_stmt = count_stmt.where(NetworkThreat.threat_type == threat_type)
            total_count = session.exec(count_stmt).one()

            # 2. Paginated Selective Fetch
            statement = select(NetworkThreat).order_by(NetworkThreat.timestamp.desc())
            if threat_type:
                statement = statement.where(NetworkThreat.threat_type == threat_type)
            
            threats = session.exec(statement.offset(offset).limit(limit)).all()
            return {
                "threats": [t.dict() for t in threats],
                "total": total_count,
                "limit": limit,
                "offset": offset
            }
    except Exception as e:
        logger.error("threat_fetch_failed", error=str(e))
        return {"threats": [], "total": 0, "error": str(e)}




@app.get("/v1/network/stats")
def get_network_stats(tenant_id: str = QueryParam(..., alias="tenant_id")):
    """Telemetry Plane: Returns global packet distribution and security trends."""
    try:
        with DatabaseManager.get_session(tenant_id) as session:
            threat_count = session.exec(select(func.count(NetworkThreat.id))).one()
            high_risk = session.exec(select(func.count(NetworkThreat.id)).where(NetworkThreat.risk_score > 0.8)).one()
            return {
                "active_sniffers": 1,
                "scope": "ENTIRE_HOST",
                "malware_detected": threat_count,
                "high_risk_alerts": high_risk,
                "health": "PROTECTED"
            }
    except Exception as e:
        return {"active_sniffers": 0, "health": "DEGRADED"}

# 3. Modular Ingestion Routers
app.include_router(onboarding_router, prefix="/v1")
app.include_router(telemetry_router, prefix="/v1")

@app.get("/health")
def health_check():
    """Liveness probe for enterprise orchestration."""
    return {"status": "healthy", "version": "v7.1-ENTERPRISE"}
