from __future__ import annotations

from backend.core.config import Settings
from backend.mcp.client import UnrealMCPClient
from backend.mcp.manager import UnrealMCPManager
from backend.mcp.mock_transport import MockUnrealTransport
from backend.mcp.registry import UnrealTransportRegistry
from backend.mcp.security import MCPSecurityPolicy
from backend.mcp.transport import UnrealTransport
from backend.mcp.transports.http_transport import HTTPUnrealTransport


def create_unreal_transport_registry() -> UnrealTransportRegistry:
    """Create a fresh registry of built-in transport builders."""
    registry = UnrealTransportRegistry()
    registry.register("mock", lambda _: MockUnrealTransport())
    registry.register("http", lambda app_settings: HTTPUnrealTransport.from_settings(app_settings))
    return registry


def create_unreal_transport(
    app_settings: Settings,
    registry: UnrealTransportRegistry | None = None,
) -> UnrealTransport:
    """Create a fresh configured transport without connecting it."""
    active_registry = registry or create_unreal_transport_registry()
    transport_name = app_settings.unreal_mcp_transport.strip().lower()
    return active_registry.get(transport_name)(app_settings)


def create_unreal_mcp_client(
    app_settings: Settings,
    registry: UnrealTransportRegistry | None = None,
) -> UnrealMCPClient:
    """Create a provider-neutral MCP client with the configured security policy."""
    transport = create_unreal_transport(app_settings, registry)
    policy = MCPSecurityPolicy(allow_write=app_settings.unreal_mcp_allow_write)
    return UnrealMCPClient(
        transport,
        security_policy=policy,
        default_timeout_seconds=app_settings.unreal_mcp_timeout_seconds,
    )


def create_unreal_mcp_manager(
    app_settings: Settings,
    registry: UnrealTransportRegistry | None = None,
) -> UnrealMCPManager:
    """Create a fresh manager with no eager network connection."""
    client = create_unreal_mcp_client(app_settings, registry)
    return UnrealMCPManager(client, auto_connect=app_settings.unreal_mcp_auto_connect)
