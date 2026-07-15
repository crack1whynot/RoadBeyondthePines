from __future__ import annotations

from backend.agents.base_agent import BaseAgent


class TaskExecutor(BaseAgent):
    """Executes tasks through provider and MCP abstractions."""

    name = "TaskExecutor"

    def run(self) -> None:
        # TODO: implement runtime execution pipeline.
        raise NotImplementedError
