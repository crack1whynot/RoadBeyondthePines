from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from backend.mcp.errors import MCPInvalidRequestError
from backend.mcp.transport import UnrealTransport

if TYPE_CHECKING:
    from backend.core.config import Settings

TransportBuilder = Callable[["Settings"], UnrealTransport]


@dataclass(slots=True)
class UnrealTransportRegistry:
    """Per-container registry of transport builders, never global transport instances."""

    _builders: dict[str, TransportBuilder] = field(default_factory=dict)

    def register(
        self,
        name: str,
        builder: TransportBuilder,
        *,
        replace: bool = False,
    ) -> None:
        """Register a transport builder and reject accidental replacement."""
        normalized_name = name.strip().lower()
        if not normalized_name:
            raise MCPInvalidRequestError("Transport name must not be empty")
        if normalized_name in self._builders and not replace:
            raise MCPInvalidRequestError(f"Transport '{normalized_name}' is already registered")
        self._builders[normalized_name] = builder

    def unregister(self, name: str) -> None:
        """Remove a registered builder if it exists."""
        self._builders.pop(name.strip().lower(), None)

    def get(self, name: str) -> TransportBuilder:
        """Return a registered builder or report an unsupported transport name."""
        normalized_name = name.strip().lower()
        builder = self._builders.get(normalized_name)
        if builder is None:
            raise MCPInvalidRequestError(f"Unsupported Unreal MCP transport '{normalized_name}'")
        return builder

    def contains(self, name: str) -> bool:
        """Return whether a named transport builder is registered."""
        return name.strip().lower() in self._builders

    def list_names(self) -> list[str]:
        """Return transport names in deterministic order."""
        return sorted(self._builders)

    def clear(self) -> None:
        """Remove all transport builders from this registry instance."""
        self._builders.clear()
