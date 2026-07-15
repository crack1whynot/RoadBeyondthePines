from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(slots=True)
class MemoryQuery:
    """Structured query parameters for retrieving memory entries."""

    category: str | None = None
    tag: str | None = None
    author: str | None = None
    date: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def matches(self, entry: Any, *, now: datetime | None = None) -> bool:
        if self.category and entry.category != self.category:
            return False
        if self.tag and self.tag not in entry.tags:
            return False
        if self.author and entry.author != self.author:
            return False
        if self.date:
            target = entry.updated_at.split("T", 1)[0]
            if target != self.date:
                return False
        return True
