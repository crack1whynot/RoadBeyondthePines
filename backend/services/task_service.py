from __future__ import annotations

from typing import Protocol


class TaskServiceProtocol(Protocol):
    """Protocol for task planning, queueing, and dispatch."""

    def list_tasks(self) -> list[dict[str, object]]:
        """Return pending task identifiers."""
        ...


class TaskService:
    """Concrete task service stub for future implementation."""

    def __init__(self) -> None:
        self._tasks: list[dict[str, object]] = [
            {"id": "task-001", "title": "Initialize project structure", "status": "complete"},
            {"id": "task-002", "title": "Wire MVP backend health", "status": "active"},
        ]

    def list_tasks(self) -> list[dict[str, object]]:
        return self._tasks
