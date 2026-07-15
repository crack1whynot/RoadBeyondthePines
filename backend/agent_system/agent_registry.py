from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from backend.agent_system.agent import BaseAgent
from backend.agent_system.agent_capability import AgentCapability
from backend.agent_system.agent_status import AgentStatus


@dataclass(slots=True)
class AgentRegistry:
    """Single source of truth for canonical ``agent_system`` instances."""

    agents: dict[str, BaseAgent] = field(default_factory=dict)

    def register(self, agent: BaseAgent, *, replace: bool = False) -> None:
        """Register an agent and reject accidental replacement by default."""

        if agent.name in self.agents and not replace:
            raise ValueError(f"Agent '{agent.name}' is already registered")
        self.agents[agent.name] = agent

    def unregister(self, agent_name: str) -> None:
        self.agents.pop(agent_name, None)

    def find(self, agent_name: str) -> BaseAgent | None:
        return self.agents.get(agent_name)

    def find_by_capability(self, capability_name: str) -> list[BaseAgent]:
        normalized = self._normalize_capability(capability_name)
        return [
            agent
            for agent in self.list_agents()
            if any(
                self._normalize_capability(capability.name) == normalized
                for capability in agent.get_capabilities()
            )
        ]

    def find_by_capabilities(self, capability_names: list[str]) -> list[BaseAgent]:
        """Return agents that support every requested capability."""

        required = {self._normalize_capability(name) for name in capability_names if name.strip()}
        if not required:
            return []
        return [
            agent
            for agent in self.list_agents()
            if required.issubset(
                {
                    self._normalize_capability(capability.name)
                    for capability in agent.get_capabilities()
                }
            )
        ]

    def list_agents(self) -> list[BaseAgent]:
        return [self.agents[name] for name in sorted(self.agents)]

    def get_status(self, agent_name: str) -> AgentStatus | None:
        agent = self.find(agent_name)
        return agent.status if agent is not None else None

    @staticmethod
    def _normalize_capability(capability_name: str) -> str:
        return capability_name.strip().casefold()
