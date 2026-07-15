from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ExecutionResult:
    task_id: str
    status: str
    output: Any = None


@dataclass
class ExecutionSummary:
    total_tasks: int
    completed_tasks: int
    failed_tasks: int
    results: list[ExecutionResult] = field(default_factory=list)


class ResultCollector:
    """Collects and summarises orchestrator execution results."""

    def collect(self, scheduled_tasks: list[Any]) -> dict[str, Any]:
        results = [ExecutionResult(task_id=task.id, status="completed") for task in scheduled_tasks]
        summary = ExecutionSummary(
            total_tasks=len(results),
            completed_tasks=len(results),
            failed_tasks=0,
            results=results,
        )
        return {
            "summary": {
                "total_tasks": summary.total_tasks,
                "completed_tasks": summary.completed_tasks,
                "failed_tasks": summary.failed_tasks,
            },
            "results": [result.__dict__ for result in results],
        }
