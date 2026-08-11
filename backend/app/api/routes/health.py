"""Health and readiness endpoints."""

from datetime import datetime, timezone

from fastapi import APIRouter

from app.core.config import settings
from app.schemas.health import HealthResponse

router = APIRouter(tags=["System"])


@router.get("/health", response_model=HealthResponse, summary="Check API health")
async def health_check() -> HealthResponse:
    """Return a small readiness response for the UI and monitoring tools."""
    return HealthResponse(
        status="healthy",
        service=settings.app_name,
        version=settings.app_version,
        environment=settings.environment,
        timestamp=datetime.now(timezone.utc),
    )

