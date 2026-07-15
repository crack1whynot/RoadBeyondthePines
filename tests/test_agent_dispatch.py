"""Focused tests for canonical AgentManager dispatch semantics."""

from __future__ import annotations

from uuid import UUID

from backend.agent_system.agent import BaseAgent
from backend.agent_system.agent_capability import AgentCapability
from backend.agent_system.agent_context import AgentContext
from backend.agent_system.agent_manager import AgentManager
from backend.agent_system.agent_metadata import AgentMetadata
from backend.agent_system.agent_registry import AgentRegistry
from backend.agent_system.agent_result import AgentResult
from backend.agent_system.agent_status import AgentStatus
from backend.agent_system.agent_task import AgentTask
from backend.agent_system.default_agents import DiagnosticAgent
from backend.core.execution import ExecutionStatus


class RecordingAgent(BaseAgent):
    def __init__(
        self,
        name: str,
        capabilities: list[str],
        *,
        enabled: bool = True,
        priority: int = 0,
        raises: bool = False,
    ) -> None:
        super().__init__(
            name=name,
            capabilities=[AgentCapability(name=capability) for capability in capabilities],
            metadata=AgentMetadata(name=name, enabled=enabled, priority=priority),
        )
        self.raises = raises
        self.status_seen_during_execute: AgentStatus | None = None
        self.executed_tasks: list[str] = []

    def execute(self, task: AgentTask, context: AgentContext) -> AgentResult:
        self.status_seen_during_execute = self.status
        self.executed_tasks.append(task.task_id)
        if self.raises:
            raise RuntimeError("private agent exception detail")
        return AgentResult.succeeded(
            task_id=task.task_id,
            agent_id=self.name,
            output={"handled_by": self.name, "parameters": task.parameters},
        )


def test_manager_selects_one_enabled_agent_that_has_all_capabilities() -> None:
    registry = AgentRegistry()
    incomplete = RecordingAgent("Incomplete", ["compile"], priority=100)
    capable = RecordingAgent("Capable", ["compile", "diagnostic"], priority=1)
    registry.register(incomplete)
    registry.register(capable)
    manager = AgentManager(registry=registry)
    task = AgentTask(required_capabilities=["compile", "diagnostic"])

    result = manager.dispatch_task(task)

    assert result.success is True
    assert result.status is ExecutionStatus.SUCCEEDED
    assert result.agent_id == "Capable"
    assert incomplete.executed_tasks == []
    assert capable.executed_tasks == [task.task_id]


def test_manager_excludes_disabled_and_offline_agents() -> None:
    registry = AgentRegistry()
    disabled = RecordingAgent("Disabled", ["diagnostic"], enabled=False, priority=100)
    offline = RecordingAgent("Offline", ["diagnostic"], priority=90)
    available = RecordingAgent("Available", ["diagnostic"], priority=1)
    offline.stop()
    registry.register(disabled)
    registry.register(offline)
    registry.register(available)
    manager = AgentManager(registry=registry)

    result = manager.dispatch_task(AgentTask(required_capabilities=["diagnostic"]))

    assert result.success is True
    assert result.agent_id == "Available"
    assert disabled.executed_tasks == []
    assert offline.executed_tasks == []


def test_manager_returns_safe_failure_when_no_capable_agent_exists() -> None:
    manager = AgentManager(registry=AgentRegistry())

    result = manager.dispatch_task(AgentTask(required_capabilities=["does-not-exist"]))

    assert result.success is False
    assert result.status is ExecutionStatus.FAILED
    assert result.error_code == "NO_CAPABLE_AGENT"
    assert result.agent_id == ""


def test_manager_transitions_selected_agent_from_busy_back_to_idle() -> None:
    registry = AgentRegistry()
    agent = RecordingAgent("Worker", ["diagnostic"])
    registry.register(agent)
    task = AgentTask(required_capabilities=["diagnostic"])

    result = AgentManager(registry=registry).dispatch_task(task)

    assert result.success is True
    assert agent.status_seen_during_execute is AgentStatus.BUSY
    assert agent.status is AgentStatus.IDLE


def test_manager_converts_agent_exception_to_safe_failure() -> None:
    registry = AgentRegistry()
    broken = RecordingAgent("Broken", ["diagnostic"], raises=True)
    registry.register(broken)

    result = AgentManager(registry=registry).dispatch_task(
        AgentTask(required_capabilities=["diagnostic"])
    )

    assert result.success is False
    assert result.status is ExecutionStatus.FAILED
    assert result.error_code == "AGENT_EXECUTION_FAILED"
    assert "private agent exception detail" not in (result.error or "")
    assert broken.status is AgentStatus.ERROR


def test_agent_result_redacts_secret_shaped_error_values() -> None:
    result = AgentResult.failed(
        task_id="safe-error",
        error="api_key=never-return-this",
        code="TEST_FAILURE",
    )

    assert result.error == "api_key=[REDACTED]"
    assert "never-return-this" not in result.to_dict()["error"]


def test_diagnostic_agent_returns_supplied_payload_and_tasks_use_uuid_ids() -> None:
    registry = AgentRegistry()
    registry.register(DiagnosticAgent())
    manager = AgentManager(registry=registry)
    first_task = AgentTask(
        required_capabilities=["diagnostic.execute"],
        parameters={"payload": {"echo": "real local operation"}},
    )
    second_task = AgentTask()

    result = manager.dispatch_task(first_task)

    assert result.success is True
    assert result.status is ExecutionStatus.SUCCEEDED
    assert result.agent_id == "DiagnosticAgent"
    assert result.output == {"echo": "real local operation"}
    assert result.output != "Handled task"
    assert UUID(first_task.task_id)
    assert UUID(second_task.task_id)
    assert first_task.task_id != second_task.task_id
