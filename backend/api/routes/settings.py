from fastapi import APIRouter, Request

from backend.core.config import settings

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("")
def get_settings(request: Request) -> dict[str, object]:
    """Expose non-sensitive application settings."""
    container = getattr(request.app.state, "container", None)
    active_settings = getattr(container, "settings", settings)
    return {
        "app_name": active_settings.app_name,
        "app_env": active_settings.app_env,
        "app_debug": active_settings.app_debug,
        "log_level": active_settings.log_level,
        "backend_host": active_settings.backend_host,
        "backend_port": active_settings.backend_port,
        "frontend_url": active_settings.frontend_url,
        "unreal_mcp_enabled": active_settings.unreal_mcp_enabled,
        "unreal_mcp_transport": active_settings.unreal_mcp_transport,
        "unreal_mcp_auto_connect": active_settings.unreal_mcp_auto_connect,
        "unreal_mcp_allow_write": active_settings.unreal_mcp_allow_write,
        "ai_provider": active_settings.ai_provider,
    }
