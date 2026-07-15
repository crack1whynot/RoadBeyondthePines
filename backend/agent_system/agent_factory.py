from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar, Type

from backend.agent_system.agent import BaseAgent
from backend.agent_system.agent_registry import AgentRegistry
from backend.agent_system.default_agents import (
    AnimationAgent,
    AudioAgent,
    DiagnosticAgent,
    DocumentationAgent,
    GameplayAgent,
    GitAgent,
    NetworkingAgent,
    ProjectManagerAgent,
    TestingAgent,
    UIAgent,
    UnrealAgent,
    VehicleAgent,
    WorldAgent,
)


@dataclass(slots=True)
class AgentFactory:
    """Creates agents using dependency injection-friendly construction."""

    registry: AgentRegistry | None = None
    # This is deliberately an opaque port.  Default agents do not import
    # transports or make direct Unreal calls; a later implementation can use
    # the DI-supplied manager behind the UnrealAgent boundary.
    unreal_mcp_manager: object | None = None

    _agent_types: ClassVar[dict[str, Type[BaseAgent]]] = {
        "diagnostic": DiagnosticAgent,
        "echo": DiagnosticAgent,
        "world": WorldAgent,
        "gameplay": GameplayAgent,
        "vehicle": VehicleAgent,
        "ui": UIAgent,
        "animation": AnimationAgent,
        "audio": AudioAgent,
        "networking": NetworkingAgent,
        "testing": TestingAgent,
        "documentation": DocumentationAgent,
        "git": GitAgent,
        "unreal": UnrealAgent,
        "project_manager": ProjectManagerAgent,
    }

    _default_agent_types: ClassVar[tuple[str, ...]] = (
        "diagnostic",
        "world",
        "gameplay",
        "vehicle",
        "ui",
        "animation",
        "audio",
        "networking",
        "testing",
        "documentation",
        "git",
        "unreal",
        "project_manager",
    )

    def create_agent(self, agent_type: str) -> BaseAgent:
        """Create and register one canonical agent instance."""

        normalized_type = agent_type.strip().casefold()
        agent_cls = self._agent_types.get(normalized_type)
        if agent_cls is None:
            raise KeyError(f"Unsupported agent type: {agent_type}")
        if normalized_type == "unreal":
            instance = UnrealAgent(mcp_manager=self.unreal_mcp_manager)
        else:
            instance = agent_cls()
        if self.registry is not None:
            self.registry.register(instance)
        return instance

    @classmethod
    def default_agent_types(cls) -> tuple[str, ...]:
        """Return the deterministic built-in set used by ``AgentLoader``."""

        return cls._default_agent_types
