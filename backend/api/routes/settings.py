from fastapi import APIRouter

from backend.core.config import settings

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("")
def get_settings() -> dict[str, object]:
    """Expose non-sensitive application settings."""
    return {
        "app_name": settings.app_name,
        "app_env": settings.app_env,
        "app_debug": settings.app_debug,
        "log_level": settings.log_level,
        "backend_host": settings.backend_host,
        "backend_port": settings.backend_port,
        "frontend_url": settings.frontend_url,
        "unreal_mcp_enabled": settings.unreal_mcp_enabled,
        "ai_provider": settings.ai_provider,
    }
