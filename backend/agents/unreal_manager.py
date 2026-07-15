from __future__ import annotations

from backend.agents.base_agent import BaseAgent


class UnrealManager(BaseAgent):
    """Abstraction for Unreal Engine operations via MCP."""

    name = "UnrealManager"

    def run(self) -> None:
        # TODO: implement Unreal Engine integration abstraction.
        raise NotImplementedError
