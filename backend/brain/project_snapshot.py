from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class ProjectSnapshot:
    """A snapshot used to describe the project at a point in time."""

    generated_at: str
    summary: str
    modules: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "generated_at": self.generated_at,
            "summary": self.summary,
            "modules": self.modules,
            "notes": self.notes,
            "metadata": self.metadata,
        }
