from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class AgentMetadata:
    """Administrative metadata for an agent."""

    name: str
    version: str = "0.1.0"
    description: str = ""
    enabled: bool = True
    priority: int = 0
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
