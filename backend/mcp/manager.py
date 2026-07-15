from __future__ import annotations

import asyncio
from typing import Any

from backend.core.logging import get_logger
from backend.mcp.client import UnrealMCPClient
from backend.mcp.errors import MCPError, MCPInvalidRequestError
from backend.mcp.models import MCPCommand, MCPCommandResult, MCPHealthStatus, UnrealConnectionInfo

logger = get_logger("mcp.manager")


class UnrealMCPManager:
    """High-level lifecycle and command boundary for all Studio Unreal MCP use."""

    def __init__(self, client: UnrealMCPClient, *, auto_connect: bool = False) -> None:
        self._client = client
        self.auto_connect = auto_connect
        self._started = False
        self._write_lock = asyncio.Lock()

    @property
    def write_enabled(self) -> bool:
        """Return whether the current security policy permits supported writes."""
        return self._client.security_policy.allow_write

    async def start(self) -> None:
        """Start manager lifecycle without requiring an Unreal Editor connection."""
        if self._started:
            return
        self._started = True
        if not self.auto_connect:
            return
        try:
            await self.connect()
        except MCPError as error:
            logger.warning("Unreal MCP auto-connect skipped: %s", error.code)

    async def stop(self) -> None:
        """Stop the manager and release any open transport resources."""
        try:
            await self.disconnect()
        except MCPError as error:
            logger.warning("Unreal MCP disconnect during shutdown failed: %s", error.code)
        finally:
            self._started = False

    async def connect(self) -> UnrealConnectionInfo:
        """Explicitly connect the active Unreal transport."""
        return await self._client.connect()

    async def disconnect(self) -> None:
        """Explicitly disconnect the active Unreal transport."""
        await self._client.disconnect()

    async def health_check(self) -> MCPHealthStatus:
        """Return health information without leaking transport exception details."""
        try:
            return await self._client.health_check()
        except MCPError as error:
            connection = self.get_connection_state()
            return MCPHealthStatus(
                healthy=False,
                connected=connection.connected,
                message=error.to_error_info().message,
                details={"code": error.code},
            )

    async def execute(
        self,
        command_name: str,
        arguments: dict[str, Any] | None = None,
    ) -> MCPCommandResult:
        """Execute one catalogued command through the active client."""
        if arguments is not None and not isinstance(arguments, dict):
            raise MCPInvalidRequestError("Command arguments must be an object")
        definition = self._client.security_policy.catalog.get(command_name)
        command = MCPCommand(
            name=command_name,
            arguments=arguments or {},
            timeout_seconds=self._client.default_timeout_seconds,
            read_only=definition.read_only,
        )
        if definition.read_only:
            return await self._client.execute(command)
        async with self._write_lock:
            return await self._client.execute(command)

    async def get_project_info(self) -> MCPCommandResult:
        return await self.execute("unreal.get_project_info")

    async def list_maps(self) -> MCPCommandResult:
        return await self.execute("unreal.list_maps")

    async def list_assets(
        self,
        path: str | None = None,
        class_name: str | None = None,
        limit: int | None = None,
    ) -> MCPCommandResult:
        arguments = {
            key: value
            for key, value in {"path": path, "class_name": class_name, "limit": limit}.items()
            if value is not None
        }
        return await self.execute("unreal.list_assets", arguments)

    def get_available_commands(self) -> list[dict[str, object]]:
        """Return safe command catalog data together with policy availability."""
        policy = self._client.security_policy
        return [
            definition.to_dict(enabled=policy.is_enabled(definition))
            for definition in policy.catalog.list_commands()
        ]

    def get_connection_state(self) -> UnrealConnectionInfo:
        """Return the most recently observed connection information."""
        return self._client.connection_info
