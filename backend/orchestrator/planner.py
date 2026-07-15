from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Protocol

from backend.core.logging import get_logger
from backend.orchestrator.execution_plan import ExecutionPlan
from backend.orchestrator.intent_analyzer import IntentAnalysis
from backend.orchestrator.task_decomposer import TaskDefinition, TaskDecomposition

logger = get_logger("orchestrator.planner")


class PlanningProvider(Protocol):
    """Provider abstraction for future AI-backed planning implementations."""

    def plan(self, intent: IntentAnalysis) -> TaskDecomposition:
        ...


class PlannerProtocol(Protocol):
    def create_plan(self, request_text: str) -> ExecutionPlan:
        ...


@dataclass
class PlannerDependencies:
    provider: PlanningProvider | None = None


class Planner:
    """Creates an execution plan from user intent."""

    def __init__(self, dependencies: PlannerDependencies | None = None) -> None:
        self.dependencies = dependencies or PlannerDependencies()

    def create_plan(self, request_text: str) -> ExecutionPlan:
        logger.info("Creating plan for request")
        intent = IntentAnalysis(request_text=request_text, intent_type="general")
        decomposition = self._default_decompose(intent)
        return ExecutionPlan(request_text=request_text, tasks=decomposition.tasks)

    def _default_decompose(self, intent: IntentAnalysis) -> TaskDecomposition:
        tasks = [
            TaskDefinition(id="task-1", name="Analyze request", capability="CompileCode", depends_on=[]),
            TaskDefinition(id="task-2", name="Prepare execution path", capability="GenerateBlueprint", depends_on=["task-1"]),
        ]
        return TaskDecomposition(tasks=tasks)
