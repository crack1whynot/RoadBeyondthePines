from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from backend.memory.memory_entry import MemoryEntry


@dataclass(slots=True)
class MemoryIndex:
    """Provides an in-memory index for memory lookups."""

    entries_by_id: dict[str, MemoryEntry] = field(default_factory=dict)

    def add(self, entry: MemoryEntry) -> None:
        self.entries_by_id[entry.id] = entry

    def remove(self, entry_id: str) -> None:
        self.entries_by_id.pop(entry_id, None)

    def get(self, entry_id: str) -> MemoryEntry | None:
        return self.entries_by_id.get(entry_id)

    def list(self) -> list[MemoryEntry]:
        return list(self.entries_by_id.values())
