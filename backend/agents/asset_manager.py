from __future__ import annotations

from backend.agents.base_agent import BaseAgent


class AssetManager(BaseAgent):
    """Coordinates asset organization and metadata management."""

    name = "AssetManager"

    def run(self) -> None:
        # TODO: implement asset lifecycle management.
        raise NotImplementedError
