from __future__ import annotations

from abc import ABC, abstractmethod


class BaseAgent(ABC):
    """Abstract base class for all studio agents."""

    name: str

    @abstractmethod
    def run(self) -> None:
        """Execute the agent's core behavior."""
        raise NotImplementedError
