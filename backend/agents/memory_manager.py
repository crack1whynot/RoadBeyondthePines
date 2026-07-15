from __future__ import annotations

from backend.agents.base_agent import BaseAgent


class MemoryManager(BaseAgent):
    """Handles long-term and short-term memory."""

    name = "MemoryManager"

    def run(self) -> None:
        # TODO: implement memory persistence and retrieval.
        raise NotImplementedError
