from __future__ import annotations

from backend.agents.base_agent import BaseAgent


class GameplayAgent(BaseAgent):
    """Agent focused on gameplay systems and logic."""

    name = "GameplayAgent"

    def run(self) -> None:
        # TODO: implement gameplay system planning and implementation hooks.
        raise NotImplementedError
