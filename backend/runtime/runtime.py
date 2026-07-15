"""Application runtime and its explicit lifecycle boundary."""

from __future__ import annotations

import threading
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Protocol

from backend.core.logging import get_logger
from backend.runtime.command_bus import CommandBus
from backend.runtime.event_bus import EventBus, RuntimeStarted, RuntimeStopped
from backend.runtime.plugin_loader import PluginLoader
from backend.runtime.service_registry import ServiceRegistry
from backend.runtime.state_manager import StateManager
from backend.runtime.task_queue import Job, JobResult, TaskQueue
from backend.runtime.worker import Worker

logger = get_logger("runtime")

RuntimeJobHandler = Callable[[Job], Any]


class RuntimeLifecycle(Protocol):
    """Lifecycle contract for runtime components."""

    def start(self) -> None:
        ...

    def stop(self) -> None:
        ...


@dataclass
class RuntimeContext:
    """Runtime-owned infrastructure components."""

    service_registry: ServiceRegistry = field(default_factory=ServiceRegistry)
    event_bus: EventBus = field(default_factory=EventBus)
    command_bus: CommandBus = field(default_factory=CommandBus)
    task_queue: TaskQueue = field(default_factory=TaskQueue)
    state_manager: StateManager = field(default_factory=StateManager)
    plugin_loader: PluginLoader = field(default_factory=PluginLoader)
    worker: Worker = field(default_factory=Worker)


class Runtime:
    """Owns handler registration, the in-process queue, and worker lifecycle.

    Constructing this class has no thread or worker side effects.  Call
    :meth:`start` (or the backwards-compatible :meth:`initialize`) during an
    application's lifespan.
    """

    def __init__(self, context: RuntimeContext | None = None) -> None:
        self.context = context or RuntimeContext()
        self._started = False
        self._stopped = False
        self._handlers: dict[str, Any] = {}
        self._handler_lock = threading.RLock()
        self._lifecycle_lock = threading.RLock()

    @property
    def running(self) -> bool:
        """Return whether the runtime lifecycle is active."""

        with self._lifecycle_lock:
            return self._started and self.context.worker.running

    def start(self) -> None:
        """Initialize infrastructure and explicitly start the worker."""

        with self._lifecycle_lock:
            if self._started:
                return

            logger.info("Starting Runtime")
            self._register_core_services()
            self.context.worker.attach_task_queue(self.context.task_queue)
            self.context.worker.attach_handler_resolver(self._resolve_handler)
            self.context.plugin_loader.attach_runtime(self)
            self.context.state_manager.initialize()
            self.context.command_bus.initialize()
            self.context.event_bus.initialize()
            self.context.task_queue.initialize()
            self.context.worker.start()
            self._started = True
            self._stopped = False
            self.context.event_bus.publish(RuntimeStarted())
            logger.info("Runtime started")

    def initialize(self) -> None:
        """Backward-compatible alias for :meth:`start`."""

        self.start()

    def stop(self) -> None:
        """Drain accepted jobs, stop the worker, and close the queue."""

        with self._lifecycle_lock:
            if self._stopped:
                return

            logger.info("Stopping Runtime")
            # Mark the runtime inactive first so callers using Runtime's API do
            # not add work while the worker is draining.
            self._started = False
            self.context.worker.stop(drain=True, timeout=5.0)
            if self.context.worker.running:
                # A synchronous handler may ignore cancellation.  Closing the
                # queue gives the worker a cooperative cancellation signal and
                # a final short join opportunity instead of pretending it has
                # already stopped.
                logger.warning("Worker exceeded graceful drain timeout; cancelling active jobs")
                self.context.task_queue.shutdown(cancel_pending=True)
                self.context.worker.stop(drain=False, timeout=1.0)
            self.context.plugin_loader.unload_all()
            self.context.task_queue.shutdown(cancel_pending=True)
            self.context.event_bus.publish(RuntimeStopped())
            self._stopped = True
            logger.info("Runtime stopped")

    def shutdown(self) -> None:
        """Backward-compatible alias for :meth:`stop`."""

        self.stop()

    def register_handler(self, name: str, handler: Any, *, replace: bool = False) -> None:
        """Register a callable or ``handle(job)`` object under a stable name."""

        if not name or not name.strip():
            raise ValueError("Handler name must be non-empty")
        if not callable(handler) and not callable(getattr(handler, "handle", None)):
            raise TypeError("Runtime handler must be callable or expose handle(job)")

        with self._handler_lock:
            if name in self._handlers and not replace:
                raise ValueError(f"Runtime handler '{name}' is already registered")
            self._handlers[name] = handler
        logger.debug("Registered runtime handler %s", name)

    def unregister_handler(self, name: str) -> bool:
        """Remove a handler.  Existing jobs then fail with HANDLER_NOT_FOUND."""

        with self._handler_lock:
            existed = name in self._handlers
            self._handlers.pop(name, None)
        if existed:
            logger.debug("Unregistered runtime handler %s", name)
        return existed

    def has_handler(self, name: str) -> bool:
        with self._handler_lock:
            return name in self._handlers

    def _resolve_handler(self, name: str) -> Any | None:
        with self._handler_lock:
            return self._handlers.get(name)

    def enqueue_job(self, job: Job) -> Job:
        """Queue an already constructed job and return the same job object."""

        with self._lifecycle_lock:
            if not self._started:
                raise RuntimeError("Runtime is not running")
            self.context.task_queue.enqueue(job)
        return job

    def get_job(self, job_id: str) -> Job | None:
        return self.context.task_queue.get_job(job_id)

    def get_job_result(self, job_id: str) -> JobResult | None:
        return self.context.task_queue.get_job_result(job_id)

    def wait_for_job(self, job_id: str, timeout: float | None = None) -> JobResult | None:
        return self.context.task_queue.wait_for_job(job_id, timeout)

    def cancel_job(self, job_id: str) -> bool:
        return self.context.task_queue.cancel(job_id)

    def get_service(self, name: str) -> object:
        """Resolve a registered service."""

        return self.context.service_registry.resolve(name)

    def register_service(self, name: str, service: object, *, replace: bool = False) -> None:
        """Register a service into the runtime registry."""

        self.context.service_registry.register(name, service, replace=replace)

    def list_services(self) -> list[str]:
        """Return all registered service names."""

        return self.context.service_registry.list_services()

    def _register_core_services(self) -> None:
        core_services = {
            "event_bus": self.context.event_bus,
            "command_bus": self.context.command_bus,
            "task_queue": self.context.task_queue,
            "state_manager": self.context.state_manager,
            "plugin_loader": self.context.plugin_loader,
            "worker": self.context.worker,
        }
        registry = self.context.service_registry
        for name, service in core_services.items():
            if registry.is_registered(name):
                if registry.resolve(name) is not service:
                    raise RuntimeError(f"Runtime core service '{name}' was replaced externally")
                continue
            registry.register(name, service)
