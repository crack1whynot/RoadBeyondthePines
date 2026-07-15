from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from backend.core.logging import get_logger
from backend.runtime.runtime import Runtime
from backend.orchestrator.planner import Planner
from backend.orchestrator.scheduler import Scheduler
from backend.orchestrator.progress_tracker import ProgressTracker
from backend.orchestrator.result_collector import ResultCollector

logger = get_logger("orchestrator")


class OrchestratorProtocol(Protocol):
    def handle_request(self, request_text: str) -> dict[str, object]:
        ...


@dataclass
class OrchestratorContext:
    runtime: Runtime
    planner: Planner
    scheduler: Scheduler
    progress_tracker: ProgressTracker
    result_collector: ResultCollector


class Orchestrator:
    """High-level coordinator that turns user intent into runtime-executed tasks."""

    def __init__(self, context: OrchestratorContext) -> None:
        self.context = context

    def handle_request(self, request_text: str) -> dict[str, object]:
        """Handle a user request end to end through the orchestrator pipeline."""
        logger.info("Handling request: %s", request_text)
        plan = self.context.planner.create_plan(request_text)
        self.context.progress_tracker.start(plan)
        scheduled = self.context.scheduler.schedule(plan)
        self.context.progress_tracker.update_from_schedule(scheduled)
        results = self.context.result_collector.collect(scheduled)
        self.context.progress_tracker.complete(plan, results)
        return {
            "request": request_text,
            "plan": plan.to_dict(),
            "scheduled_tasks": [task.to_dict() for task in scheduled],
            "results": results,
        }
