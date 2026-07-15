from __future__ import annotations

from abc import ABC, abstractmethod


class AIProvider(ABC):
    """Abstract interface for AI provider integrations."""

    @abstractmethod
    def generate(self, prompt: str) -> str:
        """Generate text or structured output from a prompt."""
        raise NotImplementedError
