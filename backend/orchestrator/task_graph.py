from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class TaskNode:
    id: str
    name: str
    capability: str
    depends_on: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class TaskGraph:
    """Dependency-aware graph for orchestrated tasks."""

    def __init__(self) -> None:
        self._nodes: dict[str, TaskNode] = {}

    def add_node(self, node: TaskNode) -> None:
        self._nodes[node.id] = node

    def add_dependency(self, parent_id: str, child_id: str) -> None:
        node = self._nodes[child_id]
        if parent_id not in node.depends_on:
            node.depends_on.append(parent_id)

    def get_nodes(self) -> list[TaskNode]:
        return list(self._nodes.values())
