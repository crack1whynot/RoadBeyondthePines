from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from backend.core.logging import get_logger
from backend.runtime.event_bus import PluginLoaded

logger = get_logger("runtime.plugin_loader")


@dataclass
class PluginMetadata:
    """Metadata contract for plugins."""

    name: str
    version: str
    enabled: bool = True
    description: str = ""


class Plugin(Protocol):
    name: str
    version: str

    def load(self) -> None:
        ...

    def unload(self) -> None:
        ...


class PluginLoaderProtocol(Protocol):
    def load_plugin(self, plugin: Plugin, metadata: PluginMetadata | None = None) -> None:
        ...

    def unload_plugin(self, plugin_name: str) -> None:
        ...

    def reload_plugin(self, plugin_name: str) -> None:
        ...

    def unload_all(self) -> None:
        ...

    def attach_runtime(self, runtime: Any) -> None:
        ...


class PluginLoader:
    """Runtime plugin loader with metadata and lifecycle support."""

    def __init__(self) -> None:
        self._plugins: dict[str, Plugin] = {}
        self._metadata: dict[str, PluginMetadata] = {}
        self._runtime: Any | None = None

    def attach_runtime(self, runtime: Any) -> None:
        self._runtime = runtime

    def load_plugin(self, plugin: Plugin, metadata: PluginMetadata | None = None) -> None:
        plugin_name = getattr(plugin, "name", plugin.__class__.__name__)
        plugin.load()
        self._plugins[plugin_name] = plugin
        self._metadata[plugin_name] = metadata or PluginMetadata(name=plugin_name, version="0.1.0")
        logger.info("Loaded plugin %s", plugin_name)
        if self._runtime is not None:
            self._runtime.context.event_bus.publish(PluginLoaded(plugin_name=plugin_name))

    def unload_plugin(self, plugin_name: str) -> None:
        plugin = self._plugins.pop(plugin_name, None)
        if plugin is not None:
            plugin.unload()
            logger.info("Unloaded plugin %s", plugin_name)

    def reload_plugin(self, plugin_name: str) -> None:
        self.unload_plugin(plugin_name)
        plugin = self._plugins.get(plugin_name)
        if plugin is not None:
            plugin.load()

    def unload_all(self) -> None:
        for plugin_name in list(self._plugins.keys()):
            self.unload_plugin(plugin_name)

    def list_plugins(self) -> list[PluginMetadata]:
        return list(self._metadata.values())
