from __future__ import annotations


class UnrealService:
    """Service abstraction for Unreal Engine automation hooks."""

    def __init__(self) -> None:
        self.connected = False

    def connect(self) -> None:
        self.connected = True

    def status(self) -> dict[str, object]:
        return {
            "connected": self.connected,
            "status": "placeholder",
            "message": "Unreal Engine integration will be added in a later milestone.",
        }
