from __future__ import annotations

from backend.agents.base_agent import BaseAgent


class AIAgent(BaseAgent):
    """General-purpose AI agent abstraction."""

    name = "AIAgent"

    def run(self) -> None:
        # TODO: implement AI reasoning workflow abstraction.
        raise NotImplementedError
