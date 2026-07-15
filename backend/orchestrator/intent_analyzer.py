from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class IntentAnalysis:
    """Represents a normalized user intent derived from a request."""

    request_text: str
    intent_type: str
    entities: list[str] = field(default_factory=list)
    confidence: float = 1.0
    metadata: dict[str, Any] = field(default_factory=dict)
