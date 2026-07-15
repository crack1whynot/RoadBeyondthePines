from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from backend.memory.memory_entry import MemoryEntry


@dataclass(slots=True)
class MemorySnapshot:
    """A point-in-time snapshot of the memory layer."""

    id: str
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    entries: list[MemoryEntry] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "created_at": self.created_at,
            "entries": [entry.to_dict() for entry in self.entries],
            "metadata": self.metadata,
        }
