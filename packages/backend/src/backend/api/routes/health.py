"""API routes for health checks."""

from contracts import HealthResponse
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.db import get_db

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Basic health check endpoint."""
    return HealthResponse()


@router.get("/health/db", response_model=HealthResponse)
async def health_check_db(db: Session = Depends(get_db)) -> HealthResponse:
    """Health check with database connectivity verification."""
    try:
        db.execute(text("SELECT 1"))
        return HealthResponse(status="ok", service="telemetry-api", version="0.1.0")
    except Exception:  # noqa: BLE001 - health check: any DB failure means "degraded"
        return HealthResponse(status="degraded", service="telemetry-api", version="0.1.0")