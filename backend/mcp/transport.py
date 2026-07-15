from __future__ import annotations

from abc import ABC, abstractmethod

from backend.mcp.models import MCPCommand, MCPCommandResult, MCPHealthStatus, UnrealConnectionInfo


class UnrealTransport(ABC):
    """Async transport boundary between Studio and an Unreal Editor bridge."""

    @abstractmethod
    async def connect(self) -> UnrealConnectionInfo:
        """Connect to the configured bridge and return public connection metadata."""
        raise NotImplementedError

    @abstractmethod
    async def disconnect(self) -> None:
        """Release any transport resources and mark the transport disconnected."""
        raise NotImplementedError

    @abstractmethod
    async def is_connected(self) -> bool:
        """Return the current transport connection state."""
        raise NotImplementedError

    @abstractmethod
    async def execute(self, command: MCPCommand) -> MCPCommandResult:
        """Execute exactly one already-authorized command."""
        raise NotImplementedError

    @abstractmethod
    async def health_check(self) -> MCPHealthStatus:
        """Return a safe transport health status."""
        raise NotImplementedError

    @abstractmethod
    def get_name(self) -> str:
        """Return the stable transport name."""
        raise NotImplementedError

    def get_capabilities(self) -> list[str]:
        """Return bridge capabilities known without a remote request."""
        return []
