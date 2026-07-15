from __future__ import annotations

import asyncio
from collections.abc import Awaitable
from typing import Any, TypeVar

from backend.core.logging import get_logger
from backend.mcp.errors import (
    MCPConnectionError,
    MCPError,
    MCPNotConnectedError,
    MCPProtocolError,
    MCPTimeoutError,
    MCPTransportError,
    MCPUnavailableError,
    MCPUnrealError,
    error_from_info,
)
from backend.mcp.models import MCPCommand, MCPCommandResult, MCPHealthStatus, UnrealConnectionInfo
from backend.mcp.security import MCPSecurityPolicy
from backend.mcp.transport import UnrealTransport

logger = get_logger("mcp.client")
_ResultT = TypeVar("_ResultT")


class UnrealMCPClient:
    """Safe async client that normalizes transport operations and command results."""

    def __init__(
        self,
        transport: UnrealTransport,
        security_policy: MCPSecurityPolicy | None = None,
        default_timeout_seconds: float = 10.0,
    ) -> None:
        if default_timeout_seconds <= 0:
            raise ValueError("default_timeout_seconds must be positive")
        self._transport = transport
        self.security_policy = security_policy or MCPSecurityPolicy()
        self.default_timeout_seconds = default_timeout_seconds
        self._connection_info = UnrealConnectionInfo(
            connected=False,
            transport=transport.get_name(),
            capabilities=transport.get_capabilities(),
        )

    @property
    def connection_info(self) -> UnrealConnectionInfo:
        """Return the last safe connection state without making a transport call."""
        return self._connection_info

    async def connect(self) -> UnrealConnectionInfo:
        """Connect the transport and retain the returned connection metadata."""
        info = await self._run_with_timeout(
            self._transport.connect(),
            timeout_seconds=self.default_timeout_seconds,
            operation_name="connect",
        )
        if not isinstance(info, UnrealConnectionInfo):
            raise MCPProtocolError("Unreal MCP transport returned invalid connection information")
        if not info.connected:
            raise MCPConnectionError("Unreal MCP transport did not establish a connection")
        normalized_info = info.model_copy(update={"transport": self._transport.get_name()})
        self._connection_info = normalized_info
        logger.info("Connected Unreal MCP transport %s", self._transport.get_name())
        return normalized_info

    async def disconnect(self) -> None:
        """Disconnect the transport and clear the retained connected state."""
        try:
            await self._run_with_timeout(
                self._transport.disconnect(),
                timeout_seconds=self.default_timeout_seconds,
                operation_name="disconnect",
            )
        finally:
            self._connection_info = self._connection_info.model_copy(update={"connected": False})
        logger.info("Disconnected Unreal MCP transport %s", self._transport.get_name())

    async def health_check(self) -> MCPHealthStatus:
        """Return normalized transport health information."""
        status = await self._run_with_timeout(
            self._transport.health_check(),
            timeout_seconds=self.default_timeout_seconds,
            operation_name="health check",
        )
        if not isinstance(status, MCPHealthStatus):
            raise MCPProtocolError("Unreal MCP transport returned invalid health information")
        self._connection_info = self._connection_info.model_copy(
            update={"connected": status.connected}
        )
        return status

    async def execute(self, command: MCPCommand) -> MCPCommandResult:
        """Authorize, time-limit, and execute one command through the transport."""
        definition = self.security_policy.validate(command)
        normalized_command = command.model_copy(update={"read_only": definition.read_only})
        connected = await self._run_with_timeout(
            self._transport.is_connected(),
            timeout_seconds=self.default_timeout_seconds,
            operation_name="connection state check",
        )
        if not connected:
            raise MCPNotConnectedError("Unreal MCP transport is not connected")

        timeout_seconds = normalized_command.timeout_seconds or self.default_timeout_seconds
        logger.info("Executing Unreal MCP command %s", normalized_command.name)
        result = await self._run_with_timeout(
            self._transport.execute(normalized_command),
            timeout_seconds=timeout_seconds,
            operation_name="command execution",
        )
        if not isinstance(result, MCPCommandResult):
            raise MCPProtocolError("Unreal MCP transport returned an invalid command result")
        if result.command_id != normalized_command.id:
            raise MCPProtocolError("Unreal MCP transport returned a mismatched command result")
        if not result.success:
            if result.error is not None:
                raise error_from_info(result.error)
            raise MCPUnrealError("Unreal MCP command failed without an error description")
        return result

    async def ping(self) -> MCPCommandResult:
        return await self._execute_named("unreal.ping")

    async def get_connection_info(self) -> MCPCommandResult:
        return await self._execute_named("unreal.get_connection_info")

    async def get_project_info(self) -> MCPCommandResult:
        return await self._execute_named("unreal.get_project_info")

    async def list_maps(self) -> MCPCommandResult:
        return await self._execute_named("unreal.list_maps")

    async def get_current_map(self) -> MCPCommandResult:
        return await self._execute_named("unreal.get_current_map")

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
        return await self._execute_named("unreal.list_assets", arguments)

    async def get_asset(self, object_path: str) -> MCPCommandResult:
        return await self._execute_named("unreal.get_asset", {"object_path": object_path})

    async def list_plugins(self) -> MCPCommandResult:
        return await self._execute_named("unreal.list_plugins")

    async def get_editor_state(self) -> MCPCommandResult:
        return await self._execute_named("unreal.get_editor_state")

    async def _execute_named(
        self,
        command_name: str,
        arguments: dict[str, Any] | None = None,
    ) -> MCPCommandResult:
        definition = self.security_policy.catalog.get(command_name)
        command = MCPCommand(
            name=command_name,
            arguments=arguments or {},
            timeout_seconds=self.default_timeout_seconds,
            read_only=definition.read_only,
        )
        return await self.execute(command)

    async def _run_with_timeout(
        self,
        operation: Awaitable[_ResultT],
        *,
        timeout_seconds: float,
        operation_name: str,
    ) -> _ResultT:
        try:
            return await asyncio.wait_for(operation, timeout=timeout_seconds)
        except asyncio.TimeoutError as error:
            raise MCPTimeoutError(
                f"Unreal MCP {operation_name} timed out",
                details={"operation": operation_name},
            ) from error
        except TimeoutError as error:
            raise MCPTimeoutError(
                f"Unreal MCP {operation_name} timed out",
                details={"operation": operation_name},
            ) from error
        except MCPError:
            raise
        except OSError as error:
            raise MCPConnectionError(
                "Unable to reach Unreal MCP transport",
                details={"operation": operation_name},
            ) from error
        except Exception as error:
            logger.warning("Unreal MCP %s failed with %s", operation_name, type(error).__name__)
            raise MCPTransportError(
                f"Unreal MCP {operation_name} failed",
                details={"operation": operation_name},
            ) from error
