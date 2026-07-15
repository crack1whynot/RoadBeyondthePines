from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass(slots=True)
class MemoryEntry:
    """A structured memory record stored by the Memory layer."""

    id: str
    title: str
    category: str
    tags: list[str] = field(default_factory=list)
    content: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    author: str = "system"
    source: str = "unknown"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "category": self.category,
            "tags": self.tags,
            "content": self.content,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "author": self.author,
            "source": self.source,
            "metadata": self.metadata,
        }
