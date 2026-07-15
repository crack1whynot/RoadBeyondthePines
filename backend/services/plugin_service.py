from __future__ import annotations


class PluginService:
    """Service abstraction for plugin loading and lifecycle management."""

    def __init__(self) -> None:
        self.plugins: list[dict[str, object]] = [
            {"name": "studio-core", "enabled": True, "status": "ready"},
            {"name": "unreal-bridge", "enabled": False, "status": "placeholder"},
        ]

    def register_plugin(self, plugin_name: str) -> None:
        self.plugins.append({"name": plugin_name, "enabled": False, "status": "registered"})

    def list_plugins(self) -> list[dict[str, object]]:
        return self.plugins
