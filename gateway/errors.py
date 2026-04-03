import structlog
from uuid import uuid4
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse

logger = structlog.get_logger()

async def global_exception_handler(request: Request, exc: Exception):
    """Fallback handler for unhandled server-side exceptions."""
    logger.error("unhandled_exception", error=str(exc), path=request.url.path)
    return JSONResponse(
        status_code=500,
        content={
            "error": "INTERNAL_SERVER_ERROR",
            "message": "An unexpected error occurred. Please contact support.",
            "trace_id": str(uuid4())
        }
    )

async def http_exception_handler(request: Request, exc: HTTPException):
    """Standardized handler for known HTTP-level errors."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": "HTTP_ERROR", "message": exc.detail}
    )

def register_error_handlers(app):
    """Binds exception handlers to the FastAPI application instance."""
    app.add_exception_handler(Exception, global_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
