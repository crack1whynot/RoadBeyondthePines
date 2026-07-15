from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from backend.core.execution import ExecutionStatus


@dataclass
class TaskDefinition:
    """A concrete unit of work in an execution plan.

    ``capability`` is retained for compatibility with the early planner API.
    The canonical dispatch contract is ``required_capabilities``: every value
    in that list must be supported by the selected agent.
    """

    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = "Diagnostic task"
    capability: str = "diagnostic.execute"
    depends_on: list[str] = field(default_factory=list)
    required_capabilities: list[str] = field(default_factory=list)
    parameters: dict[str, Any] = field(default_factory=dict)
    timeout_seconds: float | None = 5.0
    status: ExecutionStatus = ExecutionStatus.PENDING
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.required_capabilities:
            self.required_capabilities = [self.capability]
        elif self.capability not in self.required_capabilities:
            self.required_capabilities.insert(0, self.capability)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "capability": self.capability,
            "depends_on": self.depends_on,
            "required_capabilities": self.required_capabilities,
            "parameters": self.parameters,
            "timeout_seconds": self.timeout_seconds,
            "status": self.status.value,
            "metadata": self.metadata,
        }


@dataclass
class TaskDecomposition:
    tasks: list[TaskDefinition] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {"tasks": [task.to_dict() for task in self.tasks]}
