from __future__ import annotations

from dataclasses import dataclass
from typing import Type

from backend.agent_system.agent import BaseAgent
from backend.agent_system.agent_registry import AgentRegistry
from backend.agent_system.default_agents import (
    AnimationAgent,
    AudioAgent,
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

    def create_agent(self, agent_type: str) -> BaseAgent:
        agent_map: dict[str, Type[BaseAgent]] = {
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
        agent_cls = agent_map.get(agent_type)
        if agent_cls is None:
            raise KeyError(f"Unsupported agent type: {agent_type}")
        instance = agent_cls()
        if self.registry is not None:
            self.registry.register(instance)
        return instance
