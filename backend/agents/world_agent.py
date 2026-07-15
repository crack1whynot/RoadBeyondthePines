from __future__ import annotations

from backend.agents.base_agent import BaseAgent


class WorldAgent(BaseAgent):
    """Agent focused on world-building and level management."""

    name = "WorldAgent"

    def run(self) -> None:
        # TODO: implement world-level planning and validation.
        raise NotImplementedError
