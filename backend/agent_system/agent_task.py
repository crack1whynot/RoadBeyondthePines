from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4


@dataclass(slots=True)
class AgentTask:
    """A task submitted to an agent."""

    task_id: str = field(default_factory=lambda: str(uuid4()))
    priority: int = 1
    dependencies: list[str] = field(default_factory=list)
    description: str = ""
    required_capabilities: list[str] = field(default_factory=list)
    parameters: dict[str, Any] = field(default_factory=dict)
    cancellation_token: bool = False
    timeout_seconds: float | None = None
