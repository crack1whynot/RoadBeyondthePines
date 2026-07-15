from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from backend.agent_system.agent import BaseAgent
from backend.agent_system.agent_capability import AgentCapability
from backend.agent_system.agent_status import AgentStatus


@dataclass(slots=True)
class AgentRegistry:
    """Registry for provider-independent agents."""

    agents: dict[str, BaseAgent] = field(default_factory=dict)

    def register(self, agent: BaseAgent) -> None:
        self.agents[agent.name] = agent

    def unregister(self, agent_name: str) -> None:
        self.agents.pop(agent_name, None)

    def find(self, agent_name: str) -> BaseAgent | None:
        return self.agents.get(agent_name)

    def find_by_capability(self, capability_name: str) -> list[BaseAgent]:
        return [agent for agent in self.agents.values() if any(cap.name == capability_name for cap in agent.get_capabilities())]

    def list_agents(self) -> list[BaseAgent]:
        return list(self.agents.values())

    def get_status(self, agent_name: str) -> AgentStatus | None:
        agent = self.find(agent_name)
        return agent.status if agent is not None else None
