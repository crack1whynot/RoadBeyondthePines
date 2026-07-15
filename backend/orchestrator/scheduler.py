from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Protocol

from backend.core.logging import get_logger
from backend.orchestrator.execution_plan import ExecutionPlan
from backend.orchestrator.task_decomposer import TaskDefinition
from backend.runtime.runtime import Runtime
from backend.runtime.task_queue import Job, JobPriority, JobStatus

logger = get_logger("orchestrator.scheduler")


class SchedulerProtocol(Protocol):
    def schedule(self, plan: ExecutionPlan) -> list[TaskDefinition]:
        ...


@dataclass
class SchedulerDependencies:
    runtime: Runtime | None = None


class Scheduler:
    """Schedules execution plan tasks onto the runtime task queue."""

    def __init__(self, dependencies: SchedulerDependencies | None = None) -> None:
        self.dependencies = dependencies or SchedulerDependencies()

    def schedule(self, plan: ExecutionPlan) -> list[TaskDefinition]:
        logger.info("Scheduling %d tasks", len(plan.tasks))
        queue = self.dependencies.runtime.context.task_queue if self.dependencies.runtime else None
        for task in plan.tasks:
            job = Job(id=task.id, name=task.name, payload={"capability": task.capability}, priority=JobPriority.NORMAL)
            if queue is not None:
                queue.enqueue(job)
        return plan.tasks
