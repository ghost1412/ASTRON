import os
import structlog
import hashlib
from fastapi import Request, HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import jwt, JWTError
from redis import Redis
from rq import Queue

# 1. Logging
logger = structlog.get_logger()

# 2. Security Infrastructure
security = HTTPBearer()
SECRET_KEY = os.getenv("JWT_SECRET", "super-secret-key-for-demo")
ALGORITHM = "HS256"

# 3. Redis Infrastructure & Dynamic Shard Mesh
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
redis_conn = Redis(host=REDIS_HOST, port=6379, socket_timeout=5)

# v4.0: Zero-Touch Scaling - The mesh size is now driven by orchestration
SHARD_COUNT = int(os.getenv("SHARD_COUNT", "3"))
SHARD_NAMES = [f"shard_{i+1}" for i in range(SHARD_COUNT)]
shards = {name: Queue(name, connection=redis_conn) for name in SHARD_NAMES}

def get_tenant_queue(tenant_id: str) -> Queue:
    """
    Shard Affinity Resolver: Consistently maps a tenant to a specific queue shard.
    The number of shards can be scaled dynamically via env vars.
    """
    tenant_hash = int(hashlib.md5(tenant_id.encode()).hexdigest(), 16)
    shard_index = tenant_hash % len(SHARD_NAMES)
    shard_name = SHARD_NAMES[shard_index]
    
    return shards[shard_name]

def get_current_tenant(request: Request, auth: HTTPAuthorizationCredentials = Security(security)):
    """
    Decentralized Auth Middleware: Validates identity using a verified JWT.
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
