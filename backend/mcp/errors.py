from __future__ import annotations

from typing import Any

from backend.mcp.models import MCPErrorInfo, sanitize_error_message, sanitize_public_value


class MCPError(Exception):
    """Base error for the Unreal MCP layer with a safe public representation."""

    code = "mcp_error"
    retryable = False

    def __init__(
        self,
        message: str = "Unreal MCP operation failed",
        *,
        retryable: bool | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.message = sanitize_error_message(message)
        self.details = sanitize_public_value(details or {})
        self._retryable = self.retryable if retryable is None else retryable
        super().__init__(self.message)

    def to_error_info(self) -> MCPErrorInfo:
        return MCPErrorInfo(
            code=self.code,
            message=self.message,
            retryable=self._retryable,
            details=self.details,
        )


class MCPConnectionError(MCPError):
    code = "mcp_connection_error"
    retryable = True


class MCPNotConnectedError(MCPError):
    code = "mcp_not_connected"


class MCPTimeoutError(MCPError):
    code = "mcp_timeout"
    retryable = True


class MCPTransportError(MCPError):
    code = "mcp_transport_error"
    retryable = True


class MCPProtocolError(MCPError):
    code = "mcp_protocol_error"


class MCPCommandNotFoundError(MCPError):
    code = "mcp_command_not_found"


class MCPCommandRejectedError(MCPError):
    code = "mcp_command_rejected"


class MCPPermissionError(MCPError):
    code = "mcp_permission_error"


class MCPInvalidRequestError(MCPError):
    code = "mcp_invalid_request"


class MCPUnrealError(MCPError):
    code = "mcp_unreal_error"


class MCPUnavailableError(MCPError):
    code = "mcp_unavailable"
    retryable = True


_ERROR_TYPES: dict[str, type[MCPError]] = {
    error_type.code: error_type
    for error_type in (
        MCPConnectionError,
        MCPNotConnectedError,
        MCPTimeoutError,
        MCPTransportError,
        MCPProtocolError,
        MCPCommandNotFoundError,
        MCPCommandRejectedError,
        MCPPermissionError,
        MCPInvalidRequestError,
        MCPUnrealError,
        MCPUnavailableError,
    )
}


def error_from_info(error: MCPErrorInfo) -> MCPError:
    """Convert a serialized transport error into its domain exception type."""
    error_type = _ERROR_TYPES.get(error.code, MCPError)
    return error_type(error.message, retryable=error.retryable, details=error.details)
