from __future__ import annotations

from backend.agents.base_agent import BaseAgent


class AnimationAgent(BaseAgent):
    """Agent focused on animation pipelines and state logic."""

    name = "AnimationAgent"

    def run(self) -> None:
        # TODO: implement animation workflow abstractions.
        raise NotImplementedError
