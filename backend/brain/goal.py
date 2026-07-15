from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class Goal:
    """A high-level objective produced by the Brain layer."""

    id: str
    priority: int
    description: str
    required_capabilities: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    expected_result: str = ""
    constraints: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "priority": self.priority,
            "description": self.description,
            "required_capabilities": self.required_capabilities,
            "dependencies": self.dependencies,
            "expected_result": self.expected_result,
            "constraints": self.constraints,
            "metadata": self.metadata,
        }
