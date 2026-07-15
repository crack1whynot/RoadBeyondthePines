from __future__ import annotations

from typing import Protocol


class AgentServiceProtocol(Protocol):
    """Protocol for orchestrating agent lifecycle and coordination."""

    def list_agents(self) -> list[str]:
        """Return registered agent names."""
        ...


class AgentService:
    """Concrete service stub for future agent orchestration logic."""

    def list_agents(self) -> list[str]:
        # TODO: register real agents and return their names.
        return ["MainOrchestrator", "WorldAgent", "GameplayAgent"]
