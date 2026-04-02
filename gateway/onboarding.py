import secrets
from fastapi import APIRouter, HTTPException
from core.db_manager import DatabaseManager
from core.models import TenantMetadata

router = APIRouter(prefix="/v1/onboarding", tags=["Onboarding"])

@router.post("/register")
def register_tenant(company_id: str, company_name: str):
    """
    Decentralized Registration:
    Creates a dedicated database for the company and initializes their metadata locally.
    """
    # 1. Physical/Logical Database Creation
    # In production, this might be handled by an IAC script or a 
    # centralized platform API. 
    DatabaseManager.create_tenant_db(company_id)
    
    # 2. Local Metadata Initialization
    with DatabaseManager.get_session(company_id) as session:
        # Check if already initialized (idempotency)
        existing = session.get(TenantMetadata, company_id)
        if existing:
            raise HTTPException(status_code=400, detail="Company already initialized")
        
        # In this decentralized model, we generate a token. 
        # This would be registered in an Auth0/Keycloak service.
        token = f"sk_{secrets.token_urlsafe(32)}"
        
        metadata = TenantMetadata(
            company_id=company_id, 
            company_name=company_name
        )
        session.add(metadata)
        session.commit()
        
        return {
            "company_id": company_id, 
            "api_token": token,
            "message": "Decentralized database created and initialized."
        }
