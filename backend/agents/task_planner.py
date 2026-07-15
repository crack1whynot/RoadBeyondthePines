from __future__ import annotations

from backend.agents.base_agent import BaseAgent


class TaskPlanner(BaseAgent):
    """Plans tasks for the studio workflow."""

    name = "TaskPlanner"

    def run(self) -> None:
        # TODO: implement planning logic and task decomposition.
        raise NotImplementedError
