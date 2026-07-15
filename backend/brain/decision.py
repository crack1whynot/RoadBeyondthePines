from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class Decision:
    """A reasoning decision describing what should happen next."""

    kind: str
    rationale: str
    target: str
    confidence: float = 1.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "rationale": self.rationale,
            "target": self.target,
            "confidence": self.confidence,
            "metadata": self.metadata,
        }
