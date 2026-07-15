from __future__ import annotations

from dataclasses import dataclass
from importlib import import_module
from pathlib import Path
from typing import Any

from backend.agent_system.agent_factory import AgentFactory
from backend.agent_system.agent_registry import AgentRegistry
from backend.core.logging import get_logger

logger = get_logger("agent_system.loader")


@dataclass(slots=True)
class AgentLoader:
    """Discovers and loads agents from the default_agents module at startup."""

    registry: AgentRegistry
    factory: AgentFactory

    def load_all(self) -> list[str]:
        loaded: list[str] = []
        module = import_module("backend.agent_system.default_agents")
        for name in dir(module):
            value = getattr(module, name)
            if isinstance(value, type) and value.__module__ == module.__name__ and issubclass(value, object):
                try:
                    instance = value()
                    self.registry.register(instance)
                    loaded.append(instance.name)
                except Exception as exc:  # pragma: no cover - defensive path
                    logger.exception("Failed to load agent %s", name)
        return loaded
