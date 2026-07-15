from __future__ import annotations

from backend.agents.base_agent import BaseAgent


class OptimizationAgent(BaseAgent):
    """Agent focused on performance and optimization."""

    name = "OptimizationAgent"

    def run(self) -> None:
        # TODO: implement profiling and optimization strategies.
        raise NotImplementedError
