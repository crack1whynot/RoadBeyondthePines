from __future__ import annotations


class MemoryService:
    """Service contract for memory management operations."""

    def __init__(self) -> None:
        # TODO: inject persistence provider and retrieval layer.
        self._store: dict[str, object] = {}

    def save(self, key: str, value: object) -> None:
        self._store[key] = value

    def load(self, key: str) -> object | None:
        return self._store.get(key)
