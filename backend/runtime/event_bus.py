from __future__ import annotations

from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Callable, Protocol

from backend.core.logging import get_logger

logger = get_logger("runtime.event_bus")


class Event(ABC):
    """Base event contract."""

    @property
    @abstractmethod
    def event_type(self) -> str:
        ...


@dataclass
class RuntimeStarted(Event):
    event_type: str = "runtime.started"


@dataclass
class RuntimeStopped(Event):
    event_type: str = "runtime.stopped"


@dataclass
class PluginLoaded(Event):
    plugin_name: str
    event_type: str = "plugin.loaded"


class EventBusProtocol(Protocol):
    def subscribe(self, event_type: str, handler: Callable[[Event], None]) -> None:
        ...

    def unsubscribe(self, event_type: str, handler: Callable[[Event], None]) -> None:
        ...

    def publish(self, event: Event) -> None:
        ...


class EventBus:
    """Simple in-process event bus."""

    def __init__(self) -> None:
        self._handlers: dict[str, list[Callable[[Event], None]]] = defaultdict(list)

    def initialize(self) -> None:
        """Initialize the bus."""
        logger.debug("Event bus initialized")

    def subscribe(self, event_type: str, handler: Callable[[Event], None]) -> None:
        """Subscribe a handler to an event type."""
        self._handlers[event_type].append(handler)
        logger.debug("Subscribed handler for %s", event_type)

    def unsubscribe(self, event_type: str, handler: Callable[[Event], None]) -> None:
        """Unsubscribe a handler from an event type."""
        handlers = self._handlers.get(event_type, [])
        self._handlers[event_type] = [item for item in handlers if item is not handler]
        logger.debug("Unsubscribed handler for %s", event_type)

    def publish(self, event: Event) -> None:
        """Publish an event to all subscribers."""
        for handler in self._handlers.get(event.event_type, []):
            handler(event)
        logger.debug("Published event %s", event.event_type)
