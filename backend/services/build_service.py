from __future__ import annotations


class BuildService:
    """Service abstraction for build orchestration."""

    def __init__(self) -> None:
        self.builds: list[dict[str, object]] = [
            {"target": "development", "status": "queued"},
            {"target": "editor", "status": "placeholder"},
        ]

    def queue_build(self, target: str) -> None:
        self.builds.append({"target": target, "status": "queued"})

    def list_builds(self) -> list[dict[str, object]]:
        return self.builds
