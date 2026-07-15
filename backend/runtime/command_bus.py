from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Protocol

from backend.core.logging import get_logger

logger = get_logger("runtime.command_bus")


class Command(ABC):
    """Base command contract."""

    @property
    @abstractmethod
    def command_type(self) -> str:
        ...


@dataclass
class DispatchCommand(Command):
    command_type: str = "dispatch"
    payload: dict[str, Any] = field(default_factory=dict)


class CommandHandler(Protocol):
    def handle(self, command: Command) -> Any:
        ...


class Middleware(Protocol):
    def __call__(self, command: Command, next_handler: Callable[[Command], Any]) -> Any:
        ...


class CommandBusProtocol(Protocol):
    def register_handler(self, command_type: str, handler: CommandHandler) -> None:
        ...

    def register_middleware(self, middleware: Middleware) -> None:
        ...

    def dispatch(self, command: Command) -> Any:
        ...


class CommandBus:
    """Command bus with middleware support."""

    def __init__(self) -> None:
        self._handlers: dict[str, CommandHandler] = {}
        self._middlewares: list[Middleware] = []

    def initialize(self) -> None:
        """Initialize the command bus."""
        logger.debug("Command bus initialized")

    def register_handler(self, command_type: str, handler: CommandHandler) -> None:
        """Register a handler for a command type."""
        self._handlers[command_type] = handler

    def register_middleware(self, middleware: Middleware) -> None:
        """Register a middleware component."""
        self._middlewares.append(middleware)

    def dispatch(self, command: Command) -> Any:
        """Dispatch a command through registered middleware and handlers."""
        handler = self._handlers.get(command.command_type)
        if handler is None:
            raise KeyError(f"No handler registered for command '{command.command_type}'")

        def invoke(command: Command) -> Any:
            return handler.handle(command)

        for middleware in reversed(self._middlewares):
            previous = invoke
            invoke = lambda current_command, middleware=middleware, previous=previous: middleware(current_command, previous)  # type: ignore[misc]

        return invoke(command)
