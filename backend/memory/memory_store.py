from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from backend.memory.memory_entry import MemoryEntry


class MemoryStore(ABC):
    """Persistence abstraction for memory entries."""

    @abstractmethod
    def store(self, entry: MemoryEntry) -> MemoryEntry:
        ...

    @abstractmethod
    def update(self, entry: MemoryEntry) -> MemoryEntry:
        ...

    @abstractmethod
    def delete(self, entry_id: str) -> None:
        ...

    @abstractmethod
    def list_entries(self) -> list[MemoryEntry]:
        ...

    @abstractmethod
    def get(self, entry_id: str) -> MemoryEntry | None:
        ...
