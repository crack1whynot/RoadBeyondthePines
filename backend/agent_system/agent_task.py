from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class AgentTask:
    """A task submitted to an agent."""

    task_id: str
    priority: int = 1
    dependencies: list[str] = field(default_factory=list)
    description: str = ""
    required_capabilities: list[str] = field(default_factory=list)
    parameters: dict[str, Any] = field(default_factory=dict)
    cancellation_token: bool = False
