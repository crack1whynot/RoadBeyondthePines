from __future__ import annotations

from backend.agents.base_agent import BaseAgent


class TestingManager(BaseAgent):
    """Manages validation and regression testing workflows."""

    name = "TestingManager"

    def run(self) -> None:
        # TODO: implement test discovery and reporting.
        raise NotImplementedError
