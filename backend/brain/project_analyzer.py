from __future__ import annotations

from dataclasses import dataclass

from backend.brain.context import BrainContext
from backend.brain.project_snapshot import ProjectSnapshot
from backend.brain.project_state import ProjectState


@dataclass(slots=True)
class ProjectAnalyzer:
    """Analyzes the current project state and produces a summary snapshot."""

    def analyze(self, context: BrainContext) -> tuple[ProjectState, ProjectSnapshot]:
        return context.project_state, context.project_snapshot
