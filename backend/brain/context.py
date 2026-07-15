from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from backend.brain.knowledge import Knowledge
from backend.brain.project_snapshot import ProjectSnapshot
from backend.brain.project_state import ProjectState


@dataclass(slots=True)
class BrainContext:
    """The full context used by the Brain to reason about a request."""

    request_text: str
    project_state: ProjectState
    project_snapshot: ProjectSnapshot
    knowledge: Knowledge
    available_agents: list[str] = field(default_factory=list)
    available_tools: list[str] = field(default_factory=list)
    configuration: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_text": self.request_text,
            "project_state": self.project_state.to_dict(),
            "project_snapshot": self.project_snapshot.to_dict(),
            "knowledge": self.knowledge.to_dict(),
            "available_agents": self.available_agents,
            "available_tools": self.available_tools,
            "configuration": self.configuration,
            "metadata": self.metadata,
        }
