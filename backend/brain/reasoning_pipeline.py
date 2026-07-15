from __future__ import annotations

from dataclasses import dataclass

from backend.brain.context import BrainContext
from backend.brain.decision import Decision
from backend.brain.decision_engine import DecisionEngine
from backend.brain.goal import Goal


@dataclass(slots=True)
class ReasoningPipeline:
    """Transforms a context and decision into a structured goal."""

    decision_engine: DecisionEngine

    def reason(self, context: BrainContext) -> tuple[Decision, Goal]:
        decision = self.decision_engine.decide(context)
        goal = Goal(
            id="goal-001",
            priority=1,
            description=f"Understand and prepare for: {context.request_text}",
            required_capabilities=[decision.target],
            dependencies=[],
            expected_result="A clear, provider-independent goal ready for planning.",
            constraints=["No direct execution", "No direct runtime invocation"],
            metadata={"decision": decision.to_dict()},
        )
        return decision, goal
