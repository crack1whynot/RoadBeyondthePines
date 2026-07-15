from __future__ import annotations

from dataclasses import dataclass

from backend.brain.context import BrainContext
from backend.brain.decision import Decision


@dataclass(slots=True)
class DecisionEngine:
    """Determines what should happen based on the constructed context."""

    def decide(self, context: BrainContext) -> Decision:
        request = context.request_text.lower()
        if "api" in request or "endpoint" in request:
            return Decision(
                kind="define-implementation-scope",
                rationale="The request targets API surface area and should be framed as a backend change request.",
                target="backend",
                confidence=0.95,
                metadata={"area": "backend"},
            )
        if "frontend" in request or "ui" in request:
            return Decision(
                kind="define-ui-scope",
                rationale="The request targets user experience and should be framed as a frontend change request.",
                target="frontend",
                confidence=0.9,
                metadata={"area": "frontend"},
            )
        return Decision(
            kind="define-project-scope",
            rationale="The request should be understood as a general project goal that needs planning and review.",
            target="project",
            confidence=0.8,
            metadata={"area": "project"},
        )
