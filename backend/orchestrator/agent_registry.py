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
    """Legacy planning metadata registry; not used by the execution pipeline.

    Canonical runtime dispatch uses :class:`backend.agent_system.agent_registry.AgentRegistry`.
    This lightweight structure remains only to avoid breaking old imports.
    """

    def __init__(self) -> None:
        self._agents: dict[str, AgentDefinition] = {}

    def register(self, agent: AgentDefinition) -> None:
        self._agents[agent.id] = agent

    def list_agents(self) -> list[AgentDefinition]:
        return list(self._agents.values())
