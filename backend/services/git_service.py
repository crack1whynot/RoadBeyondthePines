from __future__ import annotations


class GitService:
    """Abstraction for repository operations."""

    def __init__(self) -> None:
        self.repository_path: str | None = None

    def set_repository(self, path: str) -> None:
        self.repository_path = path

    def status(self) -> dict[str, object]:
        return {
            "repository_path": self.repository_path or "not-set",
            "status": "placeholder",
            "message": "Git integration will be implemented in a later milestone.",
        }
