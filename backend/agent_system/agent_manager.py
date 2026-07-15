from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from backend.agent_system.agent import BaseAgent
from backend.agent_system.agent_context import AgentContext
from backend.agent_system.agent_registry import AgentRegistry
from backend.agent_system.agent_result import AgentResult
from backend.agent_system.agent_status import AgentStatus
from backend.agent_system.agent_task import AgentTask
from backend.core.logging import get_logger
from backend.runtime.runtime import Runtime

logger = get_logger("agent_system.manager")


@dataclass(slots=True)
class AgentManager:
    """Coordinates agent lifecycle and task dispatch."""

    registry: AgentRegistry
    runtime: Runtime | None = None
    agents: dict[str, BaseAgent] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.agents = {agent.name: agent for agent in self.registry.list_agents()}

    def start_agent(self, agent_name: str) -> None:
        agent = self.registry.find(agent_name)
        if agent is None:
            raise KeyError(f"Agent '{agent_name}' not found")
        agent.initialize()
        agent.start()

    def stop_agent(self, agent_name: str) -> None:
        agent = self.registry.find(agent_name)
        if agent is None:
            raise KeyError(f"Agent '{agent_name}' not found")
        agent.stop()

    def restart_agent(self, agent_name: str) -> None:
        self.stop_agent(agent_name)
        self.start_agent(agent_name)

    def monitor_health(self) -> dict[str, bool]:
        return {agent.name: agent.health_check() for agent in self.registry.list_agents()}

    def dispatch_task(self, task: AgentTask, context: AgentContext) -> AgentResult:
        agent = self._select_agent(task)
        if agent is None:
            return AgentResult(status=AgentStatus.ERROR, errors=["No suitable agent found"])
        agent.status = AgentStatus.BUSY
        try:
            result = agent.execute(task, context)
            return result
        except Exception as exc:  # pragma: no cover - defensive path
            logger.exception("Agent execution failed for %s", agent.name)
            return AgentResult(status=AgentStatus.ERROR, errors=[str(exc)])
        finally:
            agent.status = AgentStatus.IDLE

    def _select_agent(self, task: AgentTask) -> BaseAgent | None:
        for capability_name in task.required_capabilities:
            candidates = self.registry.find_by_capability(capability_name)
            if candidates:
                return candidates[0]
        return None
