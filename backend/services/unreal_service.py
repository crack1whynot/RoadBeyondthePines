from __future__ import annotations

from backend.mcp.manager import UnrealMCPManager


class UnrealService:
    """Backward-compatible service adapter over the DI-managed Unreal MCP manager."""

    def __init__(self, manager: UnrealMCPManager | None = None) -> None:
        self._manager = manager
        self.connected = False

    def connect(self) -> None:
        """Preserve the legacy synchronous connection marker for old callers."""
        self.connected = True

    def status(self) -> dict[str, object]:
        """Return a synchronous, safe snapshot without touching the transport."""
        if self._manager is not None:
            connection = self._manager.get_connection_state()
            return {
                "connected": connection.connected,
                "status": "connected" if connection.connected else "disconnected",
                "message": "Unreal MCP manager state",
                "transport": connection.transport,
            }
        return {
            "connected": self.connected,
            "status": "placeholder",
            "message": "Unreal Engine integration will be added in a later milestone.",
        }

    async def status_async(self) -> dict[str, object]:
        """Return manager-backed status for the existing management endpoint."""
        if self._manager is None:
            return self.status()
        health = await self._manager.health_check()
        connection = self._manager.get_connection_state()
        return {
            "connected": connection.connected,
            "status": "connected" if connection.connected else "disconnected",
            "message": health.message or "Unreal MCP manager state",
            "transport": connection.transport,
            "healthy": health.healthy,
        }
