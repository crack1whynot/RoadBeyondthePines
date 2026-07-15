from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AgentDefinition:
    id: str
    name: str
    capabilities: list[str] = field(default_factory=list)
    status: str = "idle"
    priority: int = 1
    supported_tools: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class AgentRegistry:
    """Registry of agents that can fulfill orchestrated capabilities."""

    def __init__(self) -> None:
        self._agents: dict[str, AgentDefinition] = {}

    def register(self, agent: AgentDefinition) -> None:
        self._agents[agent.id] = agent

    def list_agents(self) -> list[AgentDefinition]:
        return list(self._agents.values())
