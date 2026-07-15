from __future__ import annotations

from backend.agents.base_agent import BaseAgent


class PluginManager(BaseAgent):
    """Loads, enables, and manages studio plugins."""

    name = "PluginManager"

    def run(self) -> None:
        # TODO: implement plugin discovery and lifecycle management.
        raise NotImplementedError
