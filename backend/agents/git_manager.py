from __future__ import annotations

from backend.agents.base_agent import BaseAgent


class GitManager(BaseAgent):
    """Coordinates Git workflows for studio changes."""

    name = "GitManager"

    def run(self) -> None:
        # TODO: implement Git operations abstraction.
        raise NotImplementedError
