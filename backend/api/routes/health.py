from datetime import datetime, timezone

from fastapi import APIRouter

from backend.core.config import settings

router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
def health_check() -> dict[str, object]:
    """Return service health information."""
    return {
        "status": "ok",
        "service": settings.app_name,
        "environment": settings.app_env,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
