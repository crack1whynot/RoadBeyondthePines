from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Protocol

from backend.core.logging import get_logger
from backend.orchestrator.errors import (
    InvalidOrchestrationRequestError,
    UnsupportedRequestError,
)
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
    """Optional planning ports.

    The Provider Manager may be injected by the composition root in a future
    AI-backed planning phase.  Phase 0 deliberately does not call providers:
    only deterministic diagnostic work is supported.
    """

    provider: PlanningProvider | None = None
    provider_manager: object | None = None


class Planner:
    """Creates an execution plan from user intent."""

    def __init__(self, dependencies: PlannerDependencies | None = None) -> None:
        self.dependencies = dependencies or PlannerDependencies()

    def create_plan(self, request_text: str) -> ExecutionPlan:
        normalized_request = request_text.strip()
        if not normalized_request:
            raise InvalidOrchestrationRequestError("A request_text value is required")

        logger.info("Creating plan for request")
        intent = IntentAnalysis(request_text=normalized_request, intent_type="diagnostic")
        decomposition = self._default_decompose(intent)
        return ExecutionPlan(
            request_text=normalized_request,
            tasks=decomposition.tasks,
            metadata={"planner": "rule_based", "intent": intent.intent_type},
        )

    def _default_decompose(self, intent: IntentAnalysis) -> TaskDecomposition:
        payload = self._extract_diagnostic_payload(intent.request_text)
        tasks = [
            TaskDefinition(
                name="Execute diagnostic echo",
                capability="diagnostic.execute",
                required_capabilities=["diagnostic.execute"],
                parameters={"payload": payload},
                metadata={"intent": "diagnostic"},
            )
        ]
        return TaskDecomposition(tasks=tasks)

    @staticmethod
    def _extract_diagnostic_payload(request_text: str) -> str:
        """Accept the small, explicitly supported Phase 0 request vocabulary."""

        normalized = request_text.strip()
        lower = normalized.lower()
        for prefix in ("diagnostic:", "echo:"):
            if lower.startswith(prefix):
                return normalized[len(prefix) :].strip()
        for prefix in ("diagnostic ", "echo "):
            if lower.startswith(prefix):
                return normalized[len(prefix) :].strip()
        if lower in {"diagnostic", "echo"}:
            return ""
        raise UnsupportedRequestError(
            "Phase 0 supports only explicit diagnostic or echo requests"
        )
