from __future__ import annotations

from backend.agents.base_agent import BaseAgent
from backend.mcp.errors import MCPUnavailableError
from backend.mcp.manager import UnrealMCPManager
from backend.mcp.models import MCPCommandResult


class UnrealManager(BaseAgent):
    """Legacy agent adapter that delegates explicit reads to UnrealMCPManager."""

    name = "UnrealManager"

    def __init__(self, mcp_manager: UnrealMCPManager | None = None) -> None:
        self._mcp_manager = mcp_manager

    async def get_project_info(self) -> MCPCommandResult:
        """Read project information through the MCP manager, never a transport directly."""
        if self._mcp_manager is None:
            raise MCPUnavailableError("Unreal MCP manager is not configured")
        return await self._mcp_manager.get_project_info()

    async def list_maps(self) -> MCPCommandResult:
        """Read maps through the MCP manager, never a transport directly."""
        if self._mcp_manager is None:
            raise MCPUnavailableError("Unreal MCP manager is not configured")
        return await self._mcp_manager.list_maps()

    def run(self) -> None:
        """Keep the legacy autonomous entrypoint intentionally unsupported."""
        raise NotImplementedError
