"""Small, explicit service registry for runtime-owned infrastructure."""

from __future__ import annotations

import threading
from typing import Protocol

from backend.core.logging import get_logger

logger = get_logger("runtime.service_registry")


class ServiceRegistryProtocol(Protocol):
    """Contract for service registration and resolution."""

    def register(self, name: str, service: object, *, replace: bool = False) -> None:
        ...

    def unregister(self, name: str) -> bool:
        ...

    def resolve(self, name: str) -> object:
        ...

    def is_registered(self, name: str) -> bool:
        ...

    def list_services(self) -> list[str]:
        ...


class ServiceRegistry:
    """Thread-safe registry that never silently overwrites a service."""

    def __init__(self) -> None:
        self._services: dict[str, object] = {}
        self._lock = threading.RLock()

    def register(self, name: str, service: object, *, replace: bool = False) -> None:
        """Register a service by name, rejecting accidental replacement."""

        if not name or not name.strip():
            raise ValueError("Service name must be non-empty")
        with self._lock:
            if name in self._services and not replace:
                raise ValueError(f"Service '{name}' is already registered")
            self._services[name] = service
        logger.debug("Registered service %s", name)

    def unregister(self, name: str) -> bool:
        """Unregister a service and report whether it existed."""

        with self._lock:
            existed = name in self._services
            self._services.pop(name, None)
        if existed:
            logger.debug("Unregistered service %s", name)
        return existed

    def resolve(self, name: str) -> object:
        """Resolve a service by name."""

        with self._lock:
            if name not in self._services:
                raise KeyError(f"Service '{name}' is not registered")
            return self._services[name]

    def is_registered(self, name: str) -> bool:
        with self._lock:
            return name in self._services

    def list_services(self) -> list[str]:
        """List registered service names."""

        with self._lock:
            return sorted(self._services.keys())
