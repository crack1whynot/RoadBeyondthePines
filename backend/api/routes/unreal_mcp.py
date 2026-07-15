from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, status

from backend.core.logging import get_logger
from backend.mcp.errors import (
    MCPCommandNotFoundError,
    MCPCommandRejectedError,
    MCPConnectionError,
    MCPError,
    MCPInvalidRequestError,
    MCPNotConnectedError,
    MCPPermissionError,
    MCPProtocolError,
    MCPTimeoutError,
    MCPTransportError,
    MCPUnavailableError,
    MCPUnrealError,
)
from backend.mcp.manager import UnrealMCPManager
from backend.mcp.models import MCPExecuteRequest

logger = get_logger("api.unreal_mcp")
router = APIRouter(prefix="/unreal-mcp", tags=["unreal-mcp"])


def _get_unreal_mcp_manager(request: Request) -> UnrealMCPManager:
    container = getattr(request.app.state, "container", None)
    manager = getattr(container, "unreal_mcp_manager", None) if container is not None else None
    if manager is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "mcp_unavailable", "message": "Unreal MCP is not initialized"},
        )
    return manager


def _mcp_error_to_http_exception(error: MCPError) -> HTTPException:
    if isinstance(error, MCPInvalidRequestError):
        status_code = status.HTTP_400_BAD_REQUEST
    elif isinstance(error, MCPCommandNotFoundError):
        status_code = status.HTTP_404_NOT_FOUND
    elif isinstance(error, (MCPCommandRejectedError, MCPPermissionError)):
        status_code = status.HTTP_403_FORBIDDEN
    elif isinstance(error, (MCPConnectionError, MCPNotConnectedError, MCPUnavailableError)):
        status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    elif isinstance(error, MCPTimeoutError):
        status_code = status.HTTP_504_GATEWAY_TIMEOUT
    elif isinstance(error, (MCPProtocolError, MCPTransportError, MCPUnrealError)):
        status_code = status.HTTP_502_BAD_GATEWAY
    else:
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    return HTTPException(status_code=status_code, detail=error.to_error_info().to_dict())


@router.get("/status")
async def get_status(request: Request) -> dict[str, object]:
    """Return safe current MCP status without exposing endpoint credentials."""
    manager = _get_unreal_mcp_manager(request)
    health = await manager.health_check()
    connection = manager.get_connection_state()
    return {
        "connected": connection.connected,
        "healthy": health.healthy,
        "transport": connection.transport,
        "engine_version": connection.engine_version,
        "project_name": connection.project_name,
        "capabilities": connection.capabilities,
        "write_enabled": manager.write_enabled,
        "message": health.message,
    }


@router.get("/commands")
async def list_commands(request: Request) -> dict[str, object]:
    """List catalogued commands and their policy availability."""
    manager = _get_unreal_mcp_manager(request)
    return {"commands": manager.get_available_commands()}


@router.post("/connect")
async def connect(request: Request) -> dict[str, object]:
    """Explicitly connect the configured transport."""
    manager = _get_unreal_mcp_manager(request)
    try:
        connection = await manager.connect()
        return {"connection": connection.to_dict()}
    except MCPError as error:
        raise _mcp_error_to_http_exception(error) from error
    except Exception as error:
        logger.error("Unexpected Unreal MCP connect error: %s", type(error).__name__)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "mcp_error", "message": "Unreal MCP connection failed"},
        ) from error


@router.post("/disconnect")
async def disconnect(request: Request) -> dict[str, object]:
    """Disconnect the configured transport and release its resources."""
    manager = _get_unreal_mcp_manager(request)
    try:
        await manager.disconnect()
        connection = manager.get_connection_state()
        return {"connected": connection.connected, "transport": connection.transport}
    except MCPError as error:
        raise _mcp_error_to_http_exception(error) from error


@router.post("/execute")
async def execute(request: Request, command: MCPExecuteRequest) -> dict[str, object]:
    """Execute one safe catalogued command through the active MCP manager."""
    manager = _get_unreal_mcp_manager(request)
    try:
        result = await manager.execute(command.name, command.arguments)
        return {"result": result.to_dict()}
    except MCPError as error:
        raise _mcp_error_to_http_exception(error) from error
    except Exception as error:
        logger.error("Unexpected Unreal MCP execution error: %s", type(error).__name__)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "mcp_error", "message": "Unreal MCP command failed"},
        ) from error
