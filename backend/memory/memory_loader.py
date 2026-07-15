from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from backend.memory.memory_entry import MemoryEntry
from backend.memory.memory_serializer import MemorySerializer


class MemoryLoader:
    """Loads memory entries from disk using JSON files."""

    def __init__(self, serializer: MemorySerializer | None = None) -> None:
        self.serializer = serializer or MemorySerializer()

    def load_from_path(self, path: str | Path) -> list[MemoryEntry]:
        path = Path(path)
        if not path.exists():
            return []
        payload = json.loads(path.read_text(encoding="utf-8"))
        entries = payload.get("entries", []) if isinstance(payload, dict) else payload
        return [self.serializer.deserialize_entry(json.dumps(entry)) for entry in entries]
