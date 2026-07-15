from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class TaskDefinition:
    id: str
    name: str
    capability: str
    depends_on: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "capability": self.capability,
            "depends_on": self.depends_on,
            "metadata": self.metadata,
        }


@dataclass
class TaskDecomposition:
    tasks: list[TaskDefinition] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {"tasks": [task.to_dict() for task in self.tasks]}
