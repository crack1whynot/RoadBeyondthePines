from __future__ import annotations

from typing import Any


class WebSocketManager:
    """Central manager for real-time studio communication."""

    def __init__(self) -> None:
        self.connections: list[Any] = []

    async def register(self, connection: Any) -> None:
        # TODO: persist connection lifecycle and broadcast handling.
        self.connections.append(connection)

    async def broadcast(self, message: dict[str, Any]) -> None:
        # TODO: fan out messages to connected clients.
        raise NotImplementedError
