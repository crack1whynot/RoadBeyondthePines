from __future__ import annotations

from collections.abc import MutableMapping
from typing import Any, Protocol

from backend.core.logging import get_logger

logger = get_logger("runtime.service_registry")


class ServiceRegistryProtocol(Protocol):
    """Contract for service registration and resolution."""

    def register(self, name: str, service: object) -> None:
        ...

    def unregister(self, name: str) -> None:
        ...

    def resolve(self, name: str) -> object:
        ...

    def list_services(self) -> list[str]:
        ...


class ServiceRegistry:
    """Registry for runtime services."""

    def __init__(self) -> None:
        self._services: MutableMapping[str, object] = {}

    def register(self, name: str, service: object) -> None:
        """Register a service by name."""
        self._services[name] = service
        logger.debug("Registered service %s", name)

    def unregister(self, name: str) -> None:
        """Unregister a service by name."""
        self._services.pop(name, None)
        logger.debug("Unregistered service %s", name)

    def resolve(self, name: str) -> object:
        """Resolve a service by name."""
        if name not in self._services:
            raise KeyError(f"Service '{name}' is not registered")
        return self._services[name]

    def list_services(self) -> list[str]:
        """List registered service names."""
        return sorted(self._services.keys())
