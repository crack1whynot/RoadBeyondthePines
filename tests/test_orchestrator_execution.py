"""Execution-level tests for the truthful Phase 0 orchestrator path."""

from __future__ import annotations

from uuid import UUID

import pytest

from backend.agent_system.agent import BaseAgent
from backend.agent_system.agent_capability import AgentCapability
from backend.agent_system.agent_context import AgentContext
from backend.agent_system.agent_manager import AgentManager
from backend.agent_system.agent_metadata import AgentMetadata
from backend.agent_system.agent_registry import AgentRegistry
from backend.agent_system.agent_result import AgentResult
from backend.agent_system.agent_task import AgentTask
from backend.core.execution import ExecutionStatus
from backend.orchestrator.errors import UnsupportedRequestError
from backend.orchestrator.execution_plan import ExecutionPlan, PlanStatus
from backend.orchestrator.orchestrator import Orchestrator, OrchestratorContext
from backend.orchestrator.planner import Planner
from backend.orchestrator.progress_tracker import ProgressTracker
from backend.orchestrator.result_collector import ResultCollector
from backend.orchestrator.scheduler import Scheduler, SchedulerDependencies
from backend.orchestrator.task_decomposer import TaskDefinition
from backend.runtime.runtime import Runtime
from backend.runtime.task_queue import Job


class RecordingScheduler(Scheduler):
    """Scheduler probe that keeps the real Runtime enqueue implementation."""

    def __init__(self, dependencies: SchedulerDependencies) -> None:
        super().__init__(dependencies)
        self.jobs: list[Job] = []

    def enqueue_agent_task(
        self,
        task_definition: TaskDefinition,
        agent_task: AgentTask,
        agent_context: AgentContext,
    ) -> Job:
        job = super().enqueue_agent_task(task_definition, agent_task, agent_context)
        self.jobs.append(job)
        return job


class ControlledAgent(BaseAgent):
    """Small test agent whose returned data proves actual dispatch occurred."""

    def __init__(
        self,
        name: str,
        capabilities: list[str],
        *,
        succeed: bool = True,
    ) -> None:
        super().__init__(
            name=name,
            capabilities=[AgentCapability(name=capability) for capability in capabilities],
            metadata=AgentMetadata(name=name),
        )
        self.succeed = succeed
        self.calls: list[str] = []

    def execute(self, task: AgentTask, context: AgentContext) -> AgentResult:
        self.calls.append(task.task_id)
        if self.succeed:
            return AgentResult.succeeded(
                task_id=task.task_id,
                agent_id=self.name,
                output={"actual_payload": task.parameters.get("payload")},
            )
        return AgentResult.failed(
            task_id=task.task_id,
            agent_id=self.name,
            error="Intentional test failure",
            code="TEST_AGENT_FAILED",
        )


def _orchestrator_with(
    *agents: ControlledAgent,
) -> tuple[Runtime, Orchestrator, RecordingScheduler]:
    runtime = Runtime()
    registry = AgentRegistry()
    for agent in agents:
        registry.register(agent)
    scheduler = RecordingScheduler(SchedulerDependencies(runtime=runtime))
    orchestrator = Orchestrator(
        OrchestratorContext(
            runtime=runtime,
            planner=Planner(),
            scheduler=scheduler,
            progress_tracker=ProgressTracker(),
            result_collector=ResultCollector(),
            agent_manager=AgentManager(registry=registry, runtime=runtime),
        )
    )
    return runtime, orchestrator, scheduler


def test_planner_assigns_unique_uuids_and_rejects_unknown_execution_requests() -> None:
    planner = Planner()

    first = planner.create_plan("diagnostic: first")
    second = planner.create_plan("echo: second")

    assert UUID(first.id)
    assert UUID(second.id)
    assert UUID(first.tasks[0].id)
    assert UUID(second.tasks[0].id)
    assert first.id != second.id
    assert first.tasks[0].id != second.tasks[0].id
    assert first.tasks[0].parameters == {"payload": "first"}
    assert second.tasks[0].parameters == {"payload": "second"}

    with pytest.raises(UnsupportedRequestError, match="diagnostic or echo"):
        planner.create_plan("generate a complete Unreal gameplay system")


def test_orchestrator_queues_runtime_job_dispatches_agent_and_collects_actual_result() -> None:
    agent = ControlledAgent("EchoAgent", ["diagnostic.execute"])
    runtime, orchestrator, scheduler = _orchestrator_with(agent)
    runtime.start()
    try:
        response = orchestrator.execute_request("diagnostic: through runtime")
    finally:
        runtime.stop()

    task_result = response["results"]["results"][0]
    assert agent.calls == [task_result["task_id"]]
    assert task_result["agent_id"] == "EchoAgent"
    assert task_result["status"] == "succeeded"
    assert task_result["success"] is True
    assert task_result["output"] == {"actual_payload": "through runtime"}
    assert response["plan"]["status"] == PlanStatus.SUCCEEDED.value
    assert response["results"]["summary"] == {
        "total_tasks": 1,
        "completed_tasks": 1,
        "succeeded_tasks": 1,
        "failed_tasks": 0,
        "cancelled_tasks": 0,
        "timed_out_tasks": 0,
    }
    assert len(scheduler.jobs) == 1
    persisted_runtime_result = runtime.get_job_result(scheduler.jobs[0].id)
    assert persisted_runtime_result is not None
    assert isinstance(persisted_runtime_result.payload, AgentResult)
    assert persisted_runtime_result.payload.output == {"actual_payload": "through runtime"}


def test_orchestrator_preserves_failed_result_and_blocks_dependent_task() -> None:
    failing_agent = ControlledAgent("FailingAgent", ["test.fail"], succeed=False)
    blocked_agent = ControlledAgent("BlockedAgent", ["test.blocked"])
    runtime, orchestrator, scheduler = _orchestrator_with(failing_agent, blocked_agent)
    plan = ExecutionPlan(
        request_text="diagnostic dependency test",
        tasks=[
            TaskDefinition(id="will-fail", name="Fail", capability="test.fail"),
            TaskDefinition(
                id="must-not-run",
                name="Blocked",
                capability="test.blocked",
                depends_on=["will-fail"],
            ),
        ],
    )
    runtime.start()
    try:
        response = orchestrator.execute_plan(plan)
    finally:
        runtime.stop()

    results = {result["task_id"]: result for result in response["results"]["results"]}
    assert failing_agent.calls == ["will-fail"]
    assert blocked_agent.calls == []
    assert results["will-fail"]["status"] == ExecutionStatus.FAILED.value
    assert results["will-fail"]["success"] is False
    assert results["will-fail"]["error_code"] == "TEST_AGENT_FAILED"
    assert results["must-not-run"]["status"] == ExecutionStatus.CANCELLED.value
    assert results["must-not-run"]["success"] is False
    assert results["must-not-run"]["error_code"] == "DEPENDENCY_FAILED"
    assert response["plan"]["status"] == PlanStatus.FAILED.value
    assert len(scheduler.jobs) == 1


def test_result_collector_never_turns_absent_or_failed_work_into_completion() -> None:
    collector = ResultCollector()
    failure = AgentResult.failed(
        task_id="failed-task",
        agent_id="TestAgent",
        error="Known failure",
        code="KNOWN_FAILURE",
    )

    no_work = collector.collect([])
    failed_work = collector.collect([failure])

    assert no_work["summary"]["total_tasks"] == 0
    assert no_work["summary"]["completed_tasks"] == 0
    assert no_work["results"] == []
    assert failed_work["summary"]["total_tasks"] == 1
    assert failed_work["summary"]["completed_tasks"] == 0
    assert failed_work["summary"]["failed_tasks"] == 1
    assert failed_work["results"][0]["status"] == ExecutionStatus.FAILED.value
    assert failed_work["results"][0]["error_code"] == "KNOWN_FAILURE"
