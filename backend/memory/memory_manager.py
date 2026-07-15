from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backend.memory.memory_entry import MemoryEntry
from backend.memory.memory_history import MemoryHistory
from backend.memory.memory_index import MemoryIndex
from backend.memory.memory_loader import MemoryLoader
from backend.memory.memory_query import MemoryQuery
from backend.memory.memory_serializer import MemorySerializer
from backend.memory.memory_snapshot import MemorySnapshot
from backend.memory.memory_store import MemoryStore


@dataclass(slots=True)
class MemoryManager:
    """Coordinates storage, lookup, snapshots, and history for the Memory layer."""

    store: MemoryStore
    index: MemoryIndex | None = None
    history: MemoryHistory | None = None
    serializer: MemorySerializer | None = None
    loader: MemoryLoader | None = None
    storage_path: str | None = None

    def __post_init__(self) -> None:
        if self.index is None:
            self.index = MemoryIndex()
        if self.history is None:
            self.history = MemoryHistory()
        if self.serializer is None:
            self.serializer = MemorySerializer()
        if self.loader is None:
            self.loader = MemoryLoader(self.serializer)
        if self.storage_path is not None:
            self._load_from_disk()

    def store_entry(self, entry: MemoryEntry) -> MemoryEntry:
        stored = self.store.store(entry)
        self.index.add(stored)
        self.history.record(stored.id, "store", {"title": stored.title})
        self._persist_to_disk(stored)
        return stored

    def update_entry(self, entry: MemoryEntry) -> MemoryEntry:
        updated = self.store.update(entry)
        self.index.add(updated)
        self.history.record(updated.id, "update", {"title": updated.title})
        self._persist_to_disk(updated)
        return updated

    def delete_entry(self, entry_id: str) -> None:
        self.store.delete(entry_id)
        self.index.remove(entry_id)
        self.history.record(entry_id, "delete")
        self._persist_to_disk()

    def search_entries(self, query: MemoryQuery) -> list[MemoryEntry]:
        return [entry for entry in self.index.list() if query.matches(entry)]

    def list_entries(self) -> list[MemoryEntry]:
        return self.index.list()

    def create_snapshot(self, snapshot_id: str | None = None) -> MemorySnapshot:
        snapshot = MemorySnapshot(id=snapshot_id or f"snapshot-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}", entries=self.index.list())
        self.history.record(snapshot.id, "snapshot")
        return snapshot

    def restore_snapshot(self, snapshot: MemorySnapshot) -> None:
        for entry in snapshot.entries:
            self.index.add(entry)
            self.store.store(entry)
        self.history.record(snapshot.id, "restore", {"count": len(snapshot.entries)})

    def _persist_to_disk(self, entry: MemoryEntry | None = None) -> None:
        if self.storage_path is None:
            return
        path = Path(self.storage_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        entries = self.index.list()
        payload = {"entries": [entry.to_dict() for entry in entries]}
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def _load_from_disk(self) -> None:
        if self.storage_path is None:
            return
        path = Path(self.storage_path)
        if not path.exists():
            return
        loaded = self.loader.load_from_path(path)
        for entry in loaded:
            self.index.add(entry)
            self.store.store(entry)
