from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from backend.orchestrator.execution_plan import ExecutionPlan


class TaskState(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ProgressEntry:
    task_id: str
    state: TaskState
    message: str = ""


@dataclass
class ProgressTrackerState:
    plan_id: str | None = None
    entries: list[ProgressEntry] = field(default_factory=list)


class ProgressTracker:
    """Tracks task progress throughout execution."""

    def __init__(self) -> None:
        self._state = ProgressTrackerState()

    def start(self, plan: ExecutionPlan) -> None:
        self._state.plan_id = plan.request_text
        self._state.entries = [ProgressEntry(task_id=task.id, state=TaskState.PENDING) for task in plan.tasks]

    def update_from_schedule(self, scheduled_tasks: list[Any]) -> None:
        for task in scheduled_tasks:
            self._state.entries.append(ProgressEntry(task_id=task.id, state=TaskState.RUNNING))

    def complete(self, plan: ExecutionPlan, results: dict[str, Any]) -> None:
        self._state.entries = [ProgressEntry(task_id=task.id, state=TaskState.COMPLETED) for task in plan.tasks]

    def get_state(self) -> ProgressTrackerState:
        return self._state
