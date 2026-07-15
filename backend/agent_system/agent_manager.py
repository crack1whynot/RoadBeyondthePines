from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from backend.agent_system.agent import BaseAgent
from backend.agent_system.agent_context import AgentContext
from backend.agent_system.agent_registry import AgentRegistry
from backend.agent_system.agent_result import AgentResult
from backend.agent_system.agent_status import AgentStatus
from backend.agent_system.agent_task import AgentTask
from backend.core.execution import ExecutionStatus
from backend.core.logging import get_logger

if TYPE_CHECKING:
    from backend.runtime.runtime import Runtime


logger = get_logger("agent_system.manager")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(slots=True)
class AgentManager:
    """Dispatches canonical agent tasks against the live registry.

    This class owns selection and lifecycle transitions only.  The Runtime
    invokes this dispatcher through its registered handler; it must not cache
    registry contents because agents are loaded during application setup.
    """

    registry: AgentRegistry
    runtime: Runtime | None = None

    @property
    def agents(self) -> dict[str, BaseAgent]:
        """Compatibility view of current agents, never a startup snapshot."""

        return {agent.name: agent for agent in self.registry.list_agents()}

    def start_agent(self, agent_name: str) -> None:
        agent = self._require_agent(agent_name)
        agent.initialize()
        agent.start()

    def stop_agent(self, agent_name: str) -> None:
        self._require_agent(agent_name).stop()

    def restart_agent(self, agent_name: str) -> None:
        self.stop_agent(agent_name)
        self.start_agent(agent_name)

    def monitor_health(self) -> dict[str, bool]:
        return {agent.name: agent.health_check() for agent in self.registry.list_agents()}

    def has_capable_agent(self, required_capabilities: list[str]) -> bool:
        """Return whether an enabled, available agent supports every capability."""

        return self._select_agent_for_capabilities(required_capabilities) is not None

    def dispatch_task(self, task: AgentTask, context: AgentContext | None = None) -> AgentResult:
        """Execute one task and return only the agent's actual terminal outcome."""

        started_at = _utcnow()
        if task.cancellation_token:
            return AgentResult.failed(
                task_id=task.task_id,
                error="Task was cancelled before dispatch",
                code="TASK_CANCELLED",
                started_at=started_at,
                status=ExecutionStatus.CANCELLED,
            )

        selected_agent = self._select_agent(task)
        if selected_agent is None:
            return AgentResult.failed(
                task_id=task.task_id,
                error="No enabled agent supports all required capabilities",
                code="NO_CAPABLE_AGENT",
                started_at=started_at,
            )

        execution_context = context or AgentContext(task=task)
        selected_agent.status = AgentStatus.BUSY
        try:
            result = selected_agent.execute(task, execution_context)
        except Exception:  # pragma: no cover - defensive path covered by integration tests
            # Keep the traceback in server logs only.  Public results expose a
            # stable domain error instead of implementation details.
            logger.exception("Agent execution failed for %s", selected_agent.name)
            selected_agent.status = AgentStatus.ERROR
            return AgentResult.failed(
                task_id=task.task_id,
                agent_id=selected_agent.name,
                error="Agent execution failed",
                code="AGENT_EXECUTION_FAILED",
                started_at=started_at,
            )

        try:
            return self._normalise_result(
                result=result,
                task=task,
                agent=selected_agent,
                started_at=started_at,
            )
        finally:
            # A normal AgentResult (including NOT_IMPLEMENTED) means the
            # process is still healthy and available for a later task.  An
            # exception leaves the agent in ERROR above.
            if selected_agent.status is AgentStatus.BUSY:
                selected_agent.status = AgentStatus.IDLE

    def _select_agent(self, task: AgentTask) -> BaseAgent | None:
        return self._select_agent_for_capabilities(task.required_capabilities)

    def _select_agent_for_capabilities(self, required_capabilities: list[str]) -> BaseAgent | None:
        if not required_capabilities:
            return None

        candidates = [
            agent
            for agent in self.registry.find_by_capabilities(required_capabilities)
            if self._is_dispatchable(agent)
        ]
        if not candidates:
            return None
        return min(
            candidates,
            key=lambda agent: (-self._agent_priority(agent), agent.name.casefold()),
        )

    @staticmethod
    def _is_dispatchable(agent: BaseAgent) -> bool:
        metadata_enabled = agent.metadata.metadata.get("enabled", True)
        return (
            bool(agent.metadata.enabled)
            and bool(metadata_enabled)
            and agent.status is AgentStatus.IDLE
        )

    @staticmethod
    def _agent_priority(agent: BaseAgent) -> int:
        configured_priority = agent.metadata.metadata.get("priority", agent.metadata.priority)
        try:
            return int(configured_priority)
        except (TypeError, ValueError):
            return agent.metadata.priority

    def _normalise_result(
        self,
        *,
        result: object,
        task: AgentTask,
        agent: BaseAgent,
        started_at: datetime,
    ) -> AgentResult:
        if not isinstance(result, AgentResult):
            return AgentResult.failed(
                task_id=task.task_id,
                agent_id=agent.name,
                error="Agent returned an invalid result",
                code="INVALID_AGENT_RESULT",
                started_at=started_at,
            )

        try:
            result.status = ExecutionStatus(result.status)
        except (TypeError, ValueError):
            return AgentResult.failed(
                task_id=task.task_id,
                agent_id=agent.name,
                error="Agent returned an invalid execution status",
                code="INVALID_AGENT_RESULT",
                started_at=started_at,
            )

        if result.status not in {
            ExecutionStatus.SUCCEEDED,
            ExecutionStatus.FAILED,
            ExecutionStatus.CANCELLED,
            ExecutionStatus.TIMED_OUT,
        }:
            return AgentResult.failed(
                task_id=task.task_id,
                agent_id=agent.name,
                error="Agent returned a non-terminal result",
                code="INVALID_AGENT_RESULT",
                started_at=started_at,
            )

        # The dispatcher owns the identity and timing of this execution; an
        # agent cannot accidentally report a different task or agent.
        result.task_id = task.task_id
        result.agent_id = agent.name
        result.started_at = result.started_at or started_at
        if result.finished_at is None:
            result.complete(result.status, error=result.error)
        elif result.duration_ms is None:
            result.duration_ms = max(
                0,
                int((result.finished_at - result.started_at).total_seconds() * 1000),
            )

        if result.status is ExecutionStatus.SUCCEEDED:
            result.error = None
            result.errors.clear()
        elif not result.error:
            result.complete(result.status, error="Agent execution failed")
        return result

    def _require_agent(self, agent_name: str) -> BaseAgent:
        agent = self.registry.find(agent_name)
        if agent is None:
            raise KeyError(f"Agent '{agent_name}' not found")
        return agent
