from __future__ import annotations

from backend.agents.base_agent import BaseAgent


class UIAgent(BaseAgent):
    """Agent focused on UI and UX implementation workflows."""

    name = "UIAgent"

    def run(self) -> None:
        # TODO: implement UI-specific planning and validation.
        raise NotImplementedError
