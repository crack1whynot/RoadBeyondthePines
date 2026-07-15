from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class AgentCapability:
    """A capability an agent can fulfill."""

    name: str
    description: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
