from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from backend.core.logging import get_logger
from backend.runtime.command_bus import CommandBus
from backend.runtime.event_bus import EventBus
from backend.runtime.plugin_loader import PluginLoader
from backend.runtime.service_registry import ServiceRegistry
from backend.runtime.state_manager import StateManager
from backend.runtime.task_queue import TaskQueue
from backend.runtime.worker import Worker

logger = get_logger("runtime")


class RuntimeLifecycle(Protocol):
    """Lifecycle contract for runtime components."""

    def start(self) -> None:
        ...

    def stop(self) -> None:
        ...


@dataclass
class RuntimeContext:
    """Runtime context container."""

    service_registry: ServiceRegistry = field(default_factory=ServiceRegistry)
    event_bus: EventBus = field(default_factory=EventBus)
    command_bus: CommandBus = field(default_factory=CommandBus)
    task_queue: TaskQueue = field(default_factory=TaskQueue)
    state_manager: StateManager = field(default_factory=StateManager)
    plugin_loader: PluginLoader = field(default_factory=PluginLoader)
    worker: Worker = field(default_factory=Worker)


class Runtime:
    """Core runtime orchestrator for the application."""

    def __init__(self, context: RuntimeContext | None = None) -> None:
        self.context = context or RuntimeContext()
        self._started = False
        self._stopped = False

    def initialize(self) -> None:
        """Initialize runtime subsystems."""
        if self._started:
            return

        logger.info("Initializing Runtime")
        self.context.service_registry.register("event_bus", self.context.event_bus)
        self.context.service_registry.register("command_bus", self.context.command_bus)
        self.context.service_registry.register("task_queue", self.context.task_queue)
        self.context.service_registry.register("state_manager", self.context.state_manager)
        self.context.service_registry.register("plugin_loader", self.context.plugin_loader)
        self.context.service_registry.register("worker", self.context.worker)

        self.context.worker.attach_task_queue(self.context.task_queue)
        self.context.plugin_loader.attach_runtime(self)
        self.context.state_manager.initialize()
        self.context.command_bus.initialize()
        self.context.event_bus.initialize()
        self.context.task_queue.initialize()
        self.context.worker.start()
        self._started = True
        logger.info("Runtime initialized")

    def shutdown(self) -> None:
        """Gracefully shut down runtime subsystems."""
        if self._stopped:
            return

        logger.info("Shutting down Runtime")
        self.context.worker.stop()
        self.context.plugin_loader.unload_all()
        self.context.task_queue.shutdown()
        self._stopped = True
        logger.info("Runtime stopped")

    def get_service(self, name: str) -> object:
        """Resolve a registered service."""
        return self.context.service_registry.resolve(name)

    def register_service(self, name: str, service: object) -> None:
        """Register a service into the runtime registry."""
        self.context.service_registry.register(name, service)

    def list_services(self) -> list[str]:
        """Return all registered service names."""
        return self.context.service_registry.list_services()
