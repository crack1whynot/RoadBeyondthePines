from __future__ import annotations

from backend.agents.base_agent import BaseAgent


class BuildManager(BaseAgent):
    """Coordinates build and packaging workflows."""

    name = "BuildManager"

    def run(self) -> None:
        # TODO: implement build orchestration and logs.
        raise NotImplementedError
