from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class ProjectState:
    """A lightweight, provider-independent view of the current project state."""

    project_name: str
    root_path: str
    active_modules: list[str] = field(default_factory=list)
    recent_changes: list[str] = field(default_factory=list)
    open_issues: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_name": self.project_name,
            "root_path": self.root_path,
            "active_modules": self.active_modules,
            "recent_changes": self.recent_changes,
            "open_issues": self.open_issues,
            "metadata": self.metadata,
        }
