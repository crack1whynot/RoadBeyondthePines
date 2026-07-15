from __future__ import annotations

from abc import ABC, abstractmethod


class BaseAgent(ABC):
    """Deprecated ``run()``-based base class; use ``backend.agent_system``."""

    name: str

    @abstractmethod
    def run(self) -> None:
        """Execute the agent's core behavior."""
        raise NotImplementedError
