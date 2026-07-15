from __future__ import annotations

from backend.agents.base_agent import BaseAgent


class VehicleAgent(BaseAgent):
    """Agent focused on vehicle systems and simulation."""

    name = "VehicleAgent"

    def run(self) -> None:
        # TODO: implement vehicle-specific logic and tool integration.
        raise NotImplementedError
