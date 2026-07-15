from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class Knowledge:
    """Structured knowledge captured from documentation, memory, and conventions."""

    sources: list[str] = field(default_factory=list)
    facts: dict[str, Any] = field(default_factory=dict)
    constraints: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "sources": self.sources,
            "facts": self.facts,
            "constraints": self.constraints,
        }
