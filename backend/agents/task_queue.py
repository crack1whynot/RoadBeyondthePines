from __future__ import annotations

from backend.agents.base_agent import BaseAgent


class TaskQueue(BaseAgent):
    """Manages execution queue and prioritization."""

    name = "TaskQueue"

    def run(self) -> None:
        # TODO: implement queue persistence and scheduling.
        raise NotImplementedError
