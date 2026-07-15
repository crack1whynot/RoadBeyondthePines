from __future__ import annotations

from abc import ABC, abstractmethod


class MCPClient(ABC):
    """Legacy synchronous MCP contract retained for backward compatibility.

    New Unreal integration code uses ``backend.mcp.client.UnrealMCPClient`` and
    its async transport abstraction. This interface remains unchanged so old
    callers are not silently broken.
    """

    @abstractmethod
    def connect(self) -> None:
        """Connect to the configured MCP endpoint."""
        raise NotImplementedError

    @abstractmethod
    def disconnect(self) -> None:
        """Disconnect from the configured MCP endpoint."""
        raise NotImplementedError

    @abstractmethod
    def send(self, payload: dict[str, object]) -> dict[str, object]:
        """Send a payload to the MCP endpoint."""
        raise NotImplementedError
