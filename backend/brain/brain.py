from __future__ import annotations

from dataclasses import dataclass

from backend.brain.context_builder import ContextBuilder
from backend.brain.decision_engine import DecisionEngine
from backend.brain.goal import Goal
from backend.brain.goal_manager import GoalManager
from backend.brain.project_analyzer import ProjectAnalyzer
from backend.brain.reasoning_pipeline import ReasoningPipeline


@dataclass(slots=True)
class Brain:
    """The central reasoning component of the Studio. It understands the project without executing work."""

    context_builder: ContextBuilder
    decision_engine: DecisionEngine
    goal_manager: GoalManager | None = None
    project_analyzer: ProjectAnalyzer | None = None
    reasoning_pipeline: ReasoningPipeline | None = None

    def __post_init__(self) -> None:
        if self.goal_manager is None:
            self.goal_manager = GoalManager()
        if self.project_analyzer is None:
            self.project_analyzer = ProjectAnalyzer()
        if self.reasoning_pipeline is None:
            self.reasoning_pipeline = ReasoningPipeline(self.decision_engine)

    def analyze(self, request_text: str) -> Goal:
        """Build context, analyze the project, and return a single goal for the Planner."""
        context = self.context_builder.build(request_text)
        self.project_analyzer.analyze(context)
        _, goal = self.reasoning_pipeline.reason(context)
        self.goal_manager.add_goal(goal)
        return goal
