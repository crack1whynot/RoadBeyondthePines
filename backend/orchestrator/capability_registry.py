from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class CapabilityDefinition:
    name: str
    description: str
    metadata: dict[str, Any] = field(default_factory=dict)


class CapabilityRegistry:
    """Legacy planning metadata registry; not used for Phase 0 dispatch."""

    def __init__(self) -> None:
        self._capabilities: dict[str, CapabilityDefinition] = {}

    def register(self, capability: CapabilityDefinition) -> None:
        self._capabilities[capability.name] = capability

    def list_capabilities(self) -> list[CapabilityDefinition]:
        return list(self._capabilities.values())
