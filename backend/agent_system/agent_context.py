from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from backend.agent_system.agent_task import AgentTask
from backend.brain.context import BrainContext
from backend.memory.memory_entry import MemoryEntry


@dataclass(slots=True)
class AgentContext:
    """Context passed into an agent execution request."""

    task: AgentTask
    project_context: BrainContext | None = None
    memory_context: list[MemoryEntry] = field(default_factory=list)
    execution_context: dict[str, Any] = field(default_factory=dict)
    configuration: dict[str, Any] = field(default_factory=dict)
