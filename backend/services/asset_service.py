from __future__ import annotations


class AssetService:
    """Service abstraction for asset management workflows."""

    def __init__(self) -> None:
        self.assets: list[dict[str, object]] = [
            {"path": "assets/levels/level_01", "type": "level", "status": "ready"},
            {"path": "assets/characters/player", "type": "character", "status": "placeholder"},
        ]

    def register_asset(self, asset_path: str) -> None:
        self.assets.append({"path": asset_path, "type": "unknown", "status": "registered"})

    def list_assets(self) -> list[dict[str, object]]:
        return self.assets
