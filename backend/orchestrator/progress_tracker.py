"""In-memory observation of real execution progress."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from backend.agent_system.agent_result import AgentResult
from backend.core.execution import ExecutionStatus
from backend.orchestrator.execution_plan import ExecutionPlan


@dataclass(slots=True)
class ProgressEntry:
    task_id: str
    state: ExecutionStatus
    message: str = ""


@dataclass(slots=True)
class ProgressTrackerState:
    plan_id: str | None = None
    entries: list[ProgressEntry] = field(default_factory=list)


class ProgressTracker:
    """Tracks state transitions without manufacturing terminal success."""

    def __init__(self) -> None:
        self._state = ProgressTrackerState()

    def start(self, plan: ExecutionPlan) -> None:
        self._state.plan_id = plan.id
        self._state.entries = [
            ProgressEntry(task_id=task.id, state=ExecutionStatus.PENDING) for task in plan.tasks
        ]

    def update(self, task_id: str, state: ExecutionStatus, message: str = "") -> None:
        for entry in self._state.entries:
            if entry.task_id == task_id:
                entry.state = state
                entry.message = message
                return
        self._state.entries.append(ProgressEntry(task_id=task_id, state=state, message=message))

    def update_from_schedule(self, scheduled_tasks: list[Any]) -> None:
        """Compatibility helper for callers that have queued concrete tasks."""

        for task in scheduled_tasks:
            self.update(task.id, ExecutionStatus.QUEUED)

    def complete(self, plan: ExecutionPlan, results: dict[str, Any]) -> None:
        """Apply supplied result statuses; never overwrite them with success."""

        for result in results.get("results", []):
            task_id = str(result.get("task_id", ""))
            status_value = result.get("status")
            try:
                state = (
                    status_value
                    if isinstance(status_value, ExecutionStatus)
                    else ExecutionStatus(str(status_value))
                )
            except ValueError:
                state = ExecutionStatus.FAILED
            self.update(task_id, state)

    def update_from_agent_result(self, result: AgentResult) -> None:
        self.update(result.task_id, result.status)

    def get_state(self) -> ProgressTrackerState:
        return self._state
