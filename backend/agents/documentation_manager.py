from __future__ import annotations

from backend.agents.base_agent import BaseAgent


class DocumentationManager(BaseAgent):
    """Owns documentation generation and maintenance."""

    name = "DocumentationManager"

    def run(self) -> None:
        # TODO: implement doc generation workflow.
        raise NotImplementedError
