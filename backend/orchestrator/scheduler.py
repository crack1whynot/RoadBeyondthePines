"""Runtime queue adapter used by the orchestrator."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from backend.agent_system.agent_context import AgentContext
from backend.agent_system.agent_task import AgentTask
from backend.core.logging import get_logger
from backend.orchestrator.execution_plan import ExecutionPlan
from backend.orchestrator.task_decomposer import TaskDefinition
from backend.runtime.runtime import Runtime
from backend.runtime.task_queue import Job, JobPriority

logger = get_logger("orchestrator.scheduler")


class SchedulerProtocol(Protocol):
    def enqueue_agent_task(
        self,
        task_definition: TaskDefinition,
        agent_task: AgentTask,
        agent_context: AgentContext,
    ) -> Job:
        ...


@dataclass(slots=True)
class SchedulerDependencies:
    runtime: Runtime
    handler_name: str = "agent.dispatch"


class Scheduler:
    """Queues prepared AgentSystem tasks for the registered runtime handler."""

    def __init__(self, dependencies: SchedulerDependencies) -> None:
        self.dependencies = dependencies

    def enqueue_agent_task(
        self,
        task_definition: TaskDefinition,
        agent_task: AgentTask,
        agent_context: AgentContext,
    ) -> Job:
        """Queue one fully prepared dispatch request and return its Runtime job."""

        job = Job(
            name=task_definition.name,
            handler_name=self.dependencies.handler_name,
            payload={"agent_task": agent_task, "agent_context": agent_context},
            priority=JobPriority.NORMAL,
            timeout_seconds=task_definition.timeout_seconds,
        )
        queued = self.dependencies.runtime.enqueue_job(job)
        logger.info("Queued task %s as runtime job %s", task_definition.id, queued.id)
        return queued

    def schedule(self, plan: ExecutionPlan) -> list[TaskDefinition]:
        """Return plan tasks without dispatching incomplete legacy schedule calls.

        Dependency-aware execution requires an AgentTask and AgentContext, so
        only :meth:`enqueue_agent_task` can enqueue work.  This compatibility
        method intentionally performs no queue mutation rather than creating
        jobs with no real executor context.
        """

        return list(plan.tasks)
