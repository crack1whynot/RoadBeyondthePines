from __future__ import annotations

from abc import ABC, abstractmethod


class MCPClient(ABC):
    """Abstract interface for Unreal MCP communication."""

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
