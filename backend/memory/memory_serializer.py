from __future__ import annotations

import json
from typing import Any

from backend.memory.memory_entry import MemoryEntry
from backend.memory.memory_snapshot import MemorySnapshot


class MemorySerializer:
    """Serializes memory entries and snapshots to JSON."""

    def serialize_entry(self, entry: MemoryEntry) -> str:
        return json.dumps(entry.to_dict(), indent=2, sort_keys=True)

    def serialize_snapshot(self, snapshot: MemorySnapshot) -> str:
        return json.dumps(snapshot.to_dict(), indent=2, sort_keys=True)

    def deserialize_entry(self, payload: str) -> MemoryEntry:
        data = json.loads(payload)
        return MemoryEntry(**data)
