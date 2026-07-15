"""Aggregation of results that were actually produced by agents."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable

from backend.agent_system.agent_result import AgentResult
from backend.core.execution import ExecutionStatus


@dataclass(slots=True)
class ExecutionSummary:
    """A serialisable aggregate over actual ``AgentResult`` instances."""

    total_tasks: int
    succeeded_tasks: int
    failed_tasks: int
    cancelled_tasks: int
    timed_out_tasks: int
    results: list[AgentResult] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_tasks": self.total_tasks,
            # ``completed_tasks`` is retained as an honest compatibility key:
            # it means successful completion, never mere queue consumption.
            "completed_tasks": self.succeeded_tasks,
            "succeeded_tasks": self.succeeded_tasks,
            "failed_tasks": self.failed_tasks,
            "cancelled_tasks": self.cancelled_tasks,
            "timed_out_tasks": self.timed_out_tasks,
        }


class ResultCollector:
    """Collect and serialise only the results supplied by execution."""

    def collect(self, results: Iterable[AgentResult]) -> dict[str, Any]:
        actual_results = list(results)
        summary = ExecutionSummary(
            total_tasks=len(actual_results),
            succeeded_tasks=sum(result.status is ExecutionStatus.SUCCEEDED for result in actual_results),
            failed_tasks=sum(result.status is ExecutionStatus.FAILED for result in actual_results),
            cancelled_tasks=sum(result.status is ExecutionStatus.CANCELLED for result in actual_results),
            timed_out_tasks=sum(result.status is ExecutionStatus.TIMED_OUT for result in actual_results),
            results=actual_results,
        )
        return {
            "summary": summary.to_dict(),
            "results": [result.to_dict() for result in actual_results],
        }
