"""Dependency-aware coordination of real AgentSystem execution."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol

from backend.agent_system.agent_context import AgentContext
from backend.agent_system.agent_manager import AgentManager
from backend.agent_system.agent_result import AgentResult
from backend.agent_system.agent_task import AgentTask
from backend.brain.goal import Goal
from backend.core.execution import ExecutionStatus
from backend.core.logging import get_logger
from backend.orchestrator.errors import RuntimeUnavailableError
from backend.orchestrator.execution_plan import ExecutionPlan, PlanStatus
from backend.orchestrator.planner import Planner
from backend.orchestrator.progress_tracker import ProgressTracker
from backend.orchestrator.result_collector import ResultCollector
from backend.orchestrator.scheduler import Scheduler
from backend.orchestrator.task_decomposer import TaskDefinition
from backend.runtime.runtime import Runtime
from backend.runtime.task_queue import Job, JobResult

logger = get_logger("orchestrator")


class OrchestratorProtocol(Protocol):
    def handle_request(self, request_text: str) -> dict[str, object]:
        ...


@dataclass(slots=True)
class OrchestratorContext:
    runtime: Runtime
    planner: Planner
    scheduler: Scheduler
    progress_tracker: ProgressTracker
    result_collector: ResultCollector
    agent_manager: AgentManager
    handler_name: str = "agent.dispatch"


class Orchestrator:
    """Turn a supported request into queued work and aggregate actual results."""

    def __init__(self, context: OrchestratorContext) -> None:
        self.context = context
        self._ensure_dispatch_handler()

    def handle_request(self, request_text: str) -> dict[str, object]:
        """Compatibility entry point for executing a raw request."""

        return self.execute_request(request_text)

    def execute_goal(self, goal: Goal) -> dict[str, object]:
        """Execute the request captured in a Brain-created goal."""

        request_text = goal.metadata.get("request_text", goal.description)
        if not isinstance(request_text, str):
            request_text = goal.description
        return self.execute_request(request_text, goal=goal)

    def execute_request(self, request_text: str, *, goal: Goal | None = None) -> dict[str, object]:
        """Plan and execute a supported request through the Runtime worker."""

        plan = self.context.planner.create_plan(request_text)
        if goal is not None:
            plan.metadata["goal_id"] = goal.id
        return self.execute_plan(plan)

    def execute_plan(self, plan: ExecutionPlan) -> dict[str, object]:
        """Execute a plan in dependency order and return no synthetic results."""

        if not self.context.runtime.running:
            raise RuntimeUnavailableError("Runtime is not running")

        self.context.progress_tracker.start(plan)
        plan.status = PlanStatus.RUNNING
        results_by_task: dict[str, AgentResult] = {}
        scheduled_tasks: list[TaskDefinition] = []
        remaining = {task.id: task for task in plan.tasks}

        while remaining:
            ready_tasks = [
                task
                for task in remaining.values()
                if all(dependency_id in results_by_task for dependency_id in task.depends_on)
            ]
            if not ready_tasks:
                # A dependency refers to a missing task or forms a cycle.  No
                # work is scheduled, and every unresolved task remains honest.
                for task_id, task in list(remaining.items()):
                    result = AgentResult.failed(
                        task_id=task.id,
                        error="Task dependencies cannot be resolved",
                        code="DEPENDENCY_CYCLE_OR_MISSING",
                    )
                    self._record_task_result(task, result, results_by_task)
                    del remaining[task_id]
                break

            for task in ready_tasks:
                del remaining[task.id]
                failed_dependencies = [
                    dependency_id
                    for dependency_id in task.depends_on
                    if not results_by_task[dependency_id].success
                ]
                if failed_dependencies:
                    result = AgentResult.failed(
                        task_id=task.id,
                        error="A required dependency did not succeed",
                        code="DEPENDENCY_FAILED",
                        status=ExecutionStatus.CANCELLED,
                        metadata={"failed_dependencies": failed_dependencies},
                    )
                    self._record_task_result(task, result, results_by_task)
                    continue

                result, queued = self._execute_task(task)
                if queued:
                    scheduled_tasks.append(task)
                self._record_task_result(task, result, results_by_task)

        actual_results = [results_by_task[task.id] for task in plan.tasks if task.id in results_by_task]
        collected = self.context.result_collector.collect(actual_results)
        self.context.progress_tracker.complete(plan, collected)
        plan.status = self._derive_plan_status(actual_results)
        plan.finished_at = datetime.now(timezone.utc).isoformat()

        return {
            "request": plan.request_text,
            "plan": plan.to_dict(),
            "scheduled_tasks": [task.to_dict() for task in scheduled_tasks],
            "results": collected,
        }

    def _ensure_dispatch_handler(self) -> None:
        runtime = self.context.runtime
        if not runtime.has_handler(self.context.handler_name):
            runtime.register_handler(self.context.handler_name, self._dispatch_agent_job)

    def _dispatch_agent_job(self, job: Job) -> AgentResult:
        """Runtime handler that delegates one prepared job to AgentManager."""

        task = job.payload.get("agent_task")
        context = job.payload.get("agent_context")
        if not isinstance(task, AgentTask) or not isinstance(context, AgentContext):
            return AgentResult.failed(
                task_id=getattr(task, "task_id", job.id),
                error="Runtime job does not contain a valid agent dispatch request",
                code="INVALID_AGENT_DISPATCH_JOB",
            )
        return self.context.agent_manager.dispatch_task(task, context)

    def _execute_task(self, task: TaskDefinition) -> tuple[AgentResult, bool]:
        if not self.context.agent_manager.has_capable_agent(task.required_capabilities):
            return (
                AgentResult.failed(
                    task_id=task.id,
                    error="No enabled, available agent supports all required capabilities",
                    code="NO_CAPABLE_AGENT",
                    metadata={"required_capabilities": task.required_capabilities},
                ),
                False,
            )

        agent_task = AgentTask(
            task_id=task.id,
            description=task.name,
            dependencies=list(task.depends_on),
            required_capabilities=list(task.required_capabilities),
            parameters=dict(task.parameters),
            timeout_seconds=task.timeout_seconds,
        )
        agent_context = AgentContext(
            task=agent_task,
            execution_context={"plan_task_id": task.id, "task_metadata": dict(task.metadata)},
        )
        try:
            task.status = ExecutionStatus.QUEUED
            self.context.progress_tracker.update(task.id, ExecutionStatus.QUEUED)
            job = self.context.scheduler.enqueue_agent_task(task, agent_task, agent_context)
            wait_timeout = (task.timeout_seconds + 1.0) if task.timeout_seconds else None
            runtime_result = self.context.runtime.wait_for_job(job.id, timeout=wait_timeout)
        except (RuntimeError, ValueError) as error:
            logger.warning("Could not schedule task %s: %s", task.id, type(error).__name__)
            return (
                AgentResult.failed(
                    task_id=task.id,
                    error="Runtime could not schedule the task",
                    code="RUNTIME_UNAVAILABLE",
                ),
                False,
            )

        if runtime_result is None:
            self.context.runtime.cancel_job(job.id)
            return (
                AgentResult.failed(
                    task_id=task.id,
                    error="Runtime did not return a task result before the wait timeout",
                    code="RUNTIME_WAIT_TIMEOUT",
                    status=ExecutionStatus.TIMED_OUT,
                ),
                True,
            )
        return self._agent_result_from_job_result(task, runtime_result), True

    @staticmethod
    def _agent_result_from_job_result(task: TaskDefinition, result: JobResult) -> AgentResult:
        if isinstance(result.payload, AgentResult):
            return result.payload
        if result.status is not ExecutionStatus.SUCCEEDED:
            return AgentResult.failed(
                task_id=task.id,
                error=result.error or "Runtime task failed",
                code=result.error_code or "RUNTIME_TASK_FAILED",
                status=result.status,
                metadata=dict(result.metadata),
            )
        # A successful queue operation is insufficient without an actual
        # AgentResult.  Treat a malformed handler response as a failure.
        return AgentResult.failed(
            task_id=task.id,
            error="Runtime handler returned no AgentResult",
            code="INVALID_AGENT_HANDLER_RESULT",
        )

    def _record_task_result(
        self,
        task: TaskDefinition,
        result: AgentResult,
        results_by_task: dict[str, AgentResult],
    ) -> None:
        task.status = result.status
        results_by_task[task.id] = result
        self.context.progress_tracker.update_from_agent_result(result)

    @staticmethod
    def _derive_plan_status(results: list[AgentResult]) -> PlanStatus:
        if not results:
            return PlanStatus.FAILED
        if all(result.status is ExecutionStatus.SUCCEEDED for result in results):
            return PlanStatus.SUCCEEDED
        if all(result.status is ExecutionStatus.CANCELLED for result in results):
            return PlanStatus.CANCELLED
        if any(result.status is ExecutionStatus.SUCCEEDED for result in results):
            return PlanStatus.PARTIALLY_SUCCEEDED
        return PlanStatus.FAILED
