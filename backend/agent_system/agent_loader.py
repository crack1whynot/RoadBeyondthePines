from __future__ import annotations

from dataclasses import dataclass

from backend.agent_system.agent_factory import AgentFactory
from backend.agent_system.agent_registry import AgentRegistry


@dataclass(slots=True)
class AgentLoader:
    """Loads the fixed built-in agent set through ``AgentFactory`` only."""

    registry: AgentRegistry
    factory: AgentFactory

    def __post_init__(self) -> None:
        if self.factory.registry is None:
            self.factory.registry = self.registry
        elif self.factory.registry is not self.registry:
            raise ValueError("AgentLoader and AgentFactory must share one AgentRegistry")

    def load_all(self) -> list[str]:
        """Load built-ins deterministically and remain idempotent."""

        loaded: list[str] = []
        for agent_type in self.factory.default_agent_types():
            existing = self.registry.find(self._agent_name_for_type(agent_type))
            if existing is not None:
                loaded.append(existing.name)
                continue
            instance = self.factory.create_agent(agent_type)
            loaded.append(instance.name)
        return loaded

    @staticmethod
    def _agent_name_for_type(agent_type: str) -> str:
        """Map factory aliases to their canonical built-in instance names."""

        names = {
            "diagnostic": "DiagnosticAgent",
            "world": "WorldAgent",
            "gameplay": "GameplayAgent",
            "vehicle": "VehicleAgent",
            "ui": "UIAgent",
            "animation": "AnimationAgent",
            "audio": "AudioAgent",
            "networking": "NetworkingAgent",
            "testing": "TestingAgent",
            "documentation": "DocumentationAgent",
            "git": "GitAgent",
            "unreal": "UnrealAgent",
            "project_manager": "ProjectManagerAgent",
        }
        return names[agent_type]
