import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.brain.brain import Brain
from backend.brain.context_builder import ContextBuilder
from backend.brain.decision_engine import DecisionEngine
from backend.brain.goal import Goal
from backend.brain.project_snapshot import ProjectSnapshot
from backend.brain.project_state import ProjectState


def test_brain_analyze_returns_goal() -> None:
    brain = Brain(
        context_builder=ContextBuilder(),
        decision_engine=DecisionEngine(),
    )

    goal = brain.analyze("Add a new API endpoint for health checks")

    assert isinstance(goal, Goal)
    assert goal.description
    assert goal.required_capabilities
