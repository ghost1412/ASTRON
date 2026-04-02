import secrets
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from core.db_manager import DatabaseManager
from core.models import Tenant

router = APIRouter(prefix="/v1/onboarding", tags=["Onboarding"])

@router.post("/register")
def register_tenant(company_id: str, company_name: str):
    """Register a new company and create their private logical database."""
    with DatabaseManager.get_master_session() as session:
        # Check if already exists
        statement = select(Tenant).where(Tenant.id == company_id)
        existing = session.exec(statement).first()
        if existing:
            raise HTTPException(status_code=400, detail="Company ID already registered")
        
        # Generate a secure token
        token = f"sk_{secrets.token_urlsafe(32)}"
        
        tenant = Tenant(id=company_id, name=company_name, api_token=token)
        session.add(tenant)
        session.commit()
        
        # Create the physical/logical database
        DatabaseManager.create_tenant_db(company_id)
        
        return {"company_id": company_id, "api_token": token}
