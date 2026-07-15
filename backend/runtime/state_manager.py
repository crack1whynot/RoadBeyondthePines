from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from backend.core.logging import get_logger

logger = get_logger("runtime.state_manager")


@dataclass
class RuntimeState:
    """Global runtime state container."""

    initialized: bool = False
    services: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


class StateManager:
    """Global application state manager with persistence hooks."""

    def __init__(self) -> None:
        self._state = RuntimeState()

    def initialize(self) -> None:
        self._state.initialized = True
        logger.debug("State manager initialized")

    def get_state(self) -> RuntimeState:
        return self._state

    def set_value(self, key: str, value: Any) -> None:
        self._state.metadata[key] = value

    def get_value(self, key: str, default: Any | None = None) -> Any:
        return self._state.metadata.get(key, default)

    def persist(self) -> None:
        """Persist the runtime state to a simple in-memory snapshot."""
        logger.debug("Persisting runtime state")
