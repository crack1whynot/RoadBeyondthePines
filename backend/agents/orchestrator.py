from __future__ import annotations

from backend.agents.base_agent import BaseAgent


class MainOrchestrator(BaseAgent):
    """Top-level orchestrator for multi-agent coordination."""

    name = "MainOrchestrator"

    def run(self) -> None:
        # TODO: implement orchestration loop and agent dispatch.
        raise NotImplementedError
