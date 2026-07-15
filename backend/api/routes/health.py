from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Request

router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
async def health_check(request: Request) -> dict[str, object]:
    """Report actual local component state without requiring Unreal Editor."""

    container = getattr(request.app.state, "container", None)
    if container is None:
        return {
            "status": "degraded",
            "service": "Road Beyond the Pines Studio",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "components": {"app_initialized": False},
        }

    runtime = getattr(container, "runtime", None)
    agent_registry = getattr(container, "agent_registry", None)
    memory = getattr(container, "memory", None)
    provider_manager = getattr(container, "provider_manager", None)
    mcp_manager = getattr(container, "unreal_mcp_manager", None)
    mcp: dict[str, object] = {"available": mcp_manager is not None, "healthy": False}
    if mcp_manager is not None:
        try:
            mcp_health = await mcp_manager.health_check()
            connection = mcp_manager.get_connection_state()
            mcp.update(
                {
                    "healthy": mcp_health.healthy,
                    "connected": connection.connected,
                    "transport": connection.transport,
                }
            )
        except Exception as error:  # Health must tolerate disabled/offline Unreal.
            mcp["error"] = type(error).__name__

    components = {
        "app_initialized": True,
        "runtime_running": bool(getattr(runtime, "running", False)),
        "agents_loaded": bool(agent_registry and agent_registry.list_agents()),
        "memory_available": memory is not None,
        "provider_manager_available": provider_manager is not None,
        "mcp": mcp,
    }
    core_healthy = all(
        (
            components["app_initialized"],
            components["runtime_running"],
            components["agents_loaded"],
            components["memory_available"],
            components["provider_manager_available"],
        )
    )
    app_settings = getattr(container, "settings", None)
    return {
        "status": "ok" if core_healthy else "degraded",
        "service": getattr(app_settings, "app_name", "Road Beyond the Pines Studio"),
        "environment": getattr(app_settings, "app_env", "unknown"),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "components": components,
    }
