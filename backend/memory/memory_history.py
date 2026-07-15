from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass(slots=True)
class MemoryHistoryEntry:
    """A single mutation event recorded for memory entries."""

    timestamp: str
    entry_id: str
    action: str
    details: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class MemoryHistory:
    """Tracks all modifications applied to the memory layer."""

    events: list[MemoryHistoryEntry] = field(default_factory=list)

    def record(self, entry_id: str, action: str, details: dict[str, Any] | None = None) -> None:
        self.events.append(
            MemoryHistoryEntry(
                timestamp=datetime.now(timezone.utc).isoformat(),
                entry_id=entry_id,
                action=action,
                details=details or {},
            )
        )

    def list_events(self) -> list[MemoryHistoryEntry]:
        return list(self.events)
