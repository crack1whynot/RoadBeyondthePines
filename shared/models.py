from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class AgentRole(str, Enum):
    MAIN_ORCHESTRATOR = "MainOrchestrator"
    TASK_PLANNER = "TaskPlanner"
    TASK_QUEUE = "TaskQueue"
    TASK_EXECUTOR = "TaskExecutor"
    MEMORY_MANAGER = "MemoryManager"
    DOCUMENTATION_MANAGER = "DocumentationManager"
    GIT_MANAGER = "GitManager"
    UNREAL_MANAGER = "UnrealManager"
    ASSET_MANAGER = "AssetManager"
    TESTING_MANAGER = "TestingManager"
    BUILD_MANAGER = "BuildManager"
    PLUGIN_MANAGER = "PluginManager"
    WORLD_AGENT = "WorldAgent"
    GAMEPLAY_AGENT = "GameplayAgent"
    VEHICLE_AGENT = "VehicleAgent"
    AI_AGENT = "AIAgent"
    UI_AGENT = "UIAgent"
    ANIMATION_AGENT = "AnimationAgent"
    OPTIMIZATION_AGENT = "OptimizationAgent"
    AUDIO_AGENT = "AudioAgent"
    NETWORKING_AGENT = "NetworkingAgent"


@dataclass
class BaseEntity:
    id: str
    created_at: str | None = None
    updated_at: str | None = None


@dataclass
class TaskRecord(BaseEntity):
    title: str
    description: str | None = None
    status: str = "pending"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentRecord(BaseEntity):
    name: str
    role: AgentRole
    enabled: bool = True


@dataclass
class ProjectContext(BaseEntity):
    name: str
    root_path: str
    metadata: dict[str, Any] = field(default_factory=dict)
