from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backend.brain.context import BrainContext
from backend.brain.knowledge import Knowledge
from backend.brain.project_snapshot import ProjectSnapshot
from backend.brain.project_state import ProjectState
from backend.core.config import Settings, settings


@dataclass(slots=True)
class ContextBuilder:
    """Builds a provider-independent context object from the current project state."""

    project_root: str | None = None
    app_settings: Settings | None = None

    def build(self, request_text: str, *, available_agents: list[str] | None = None, available_tools: list[str] | None = None) -> BrainContext:
        active_settings = self.app_settings or settings
        root = Path(self.project_root or ".").resolve()
        state = ProjectState(
            project_name="Road Beyond the Pines Studio",
            root_path=str(root),
            active_modules=["backend", "frontend", "shared", "docs"],
            recent_changes=["Runtime layer implemented", "Orchestrator layer implemented"],
            open_issues=[],
            metadata={"environment": active_settings.app_env},
        )
        snapshot = ProjectSnapshot(
            generated_at=datetime.now(timezone.utc).isoformat(),
            summary="A modular full-stack development studio with runtime and orchestrator layers.",
            modules=["backend", "frontend", "shared", "docs"],
            notes=["The Brain layer is provider-independent and reasoning-focused."],
            metadata={"backend": "FastAPI", "frontend": "React"},
        )
        knowledge = Knowledge(
            sources=["README.md", "docs/architecture.md", "docs/runtime.md", "docs/setup.md"],
            facts={
                "app_name": active_settings.app_name,
                "environment": active_settings.app_env,
                "runtime_ready": True,
                "orchestrator_ready": True,
            },
            constraints=["Do not execute tasks directly", "Do not call runtime directly", "Remain provider-independent"],
        )
        return BrainContext(
            request_text=request_text,
            project_state=state,
            project_snapshot=snapshot,
            knowledge=knowledge,
            available_agents=available_agents or ["planner", "analyst", "reviewer"],
            available_tools=available_tools or ["filesystem", "git", "tests"],
            configuration={"environment": active_settings.app_env, "debug": active_settings.app_debug},
            metadata={"project_root": str(root)},
        )
