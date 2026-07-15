from __future__ import annotations

from dataclasses import dataclass

from backend.memory.memory_entry import MemoryEntry
from backend.memory.memory_manager import MemoryManager
from backend.memory.memory_store import MemoryStore


class InMemoryStore(MemoryStore):
    """A simple in-process implementation of the memory storage abstraction."""

    def __init__(self) -> None:
        self._entries: dict[str, MemoryEntry] = {}

    def store(self, entry: MemoryEntry) -> MemoryEntry:
        self._entries[entry.id] = entry
        return entry

    def update(self, entry: MemoryEntry) -> MemoryEntry:
        self._entries[entry.id] = entry
        return entry

    def delete(self, entry_id: str) -> None:
        self._entries.pop(entry_id, None)

    def list_entries(self) -> list[MemoryEntry]:
        return list(self._entries.values())

    def get(self, entry_id: str) -> MemoryEntry | None:
        return self._entries.get(entry_id)


@dataclass(slots=True)
class ProjectMemory(MemoryManager):
    """A production-oriented façade for the Memory layer."""

    store: MemoryStore

    def __post_init__(self) -> None:
        MemoryManager.__post_init__(self)
