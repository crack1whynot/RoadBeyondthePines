import asyncio
import json
import sys
from pathlib import Path
from types import SimpleNamespace

from fastapi import HTTPException

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.api.routes.unreal_mcp import connect, disconnect, execute, get_status
from backend.core.config import Settings
from backend.mcp.factory import create_unreal_mcp_manager
from backend.mcp.models import MCPExecuteRequest


def _request_for(manager: object) -> SimpleNamespace:
    container = SimpleNamespace(unreal_mcp_manager=manager)
    app = SimpleNamespace(state=SimpleNamespace(container=container))
    return SimpleNamespace(app=app)


def _mock_manager(*, auth_token: str | None = None):
    app_settings = Settings(
        unreal_mcp_transport="mock",
        unreal_mcp_auto_connect=False,
        unreal_mcp_allow_write=False,
        unreal_mcp_auth_token=auth_token,
    )
    return create_unreal_mcp_manager(app_settings)


def test_unreal_mcp_status_connect_disconnect_and_never_exposes_auth_token() -> None:
    secret = "test-unreal-mcp-auth-token"
    manager = _mock_manager(auth_token=secret)
    request = _request_for(manager)

    async def exercise_routes() -> tuple[
        dict[str, object],
        dict[str, object],
        dict[str, object],
        dict[str, object],
    ]:
        status_before = await get_status(request)
        connected = await connect(request)
        status_after = await get_status(request)
        disconnected = await disconnect(request)
        return status_before, connected, status_after, disconnected

    try:
        status_before, connected, status_after, disconnected = asyncio.run(exercise_routes())
    finally:
        asyncio.run(manager.stop())

    assert status_before["connected"] is False
    assert status_before["healthy"] is False
    assert status_before["transport"] == "mock"
    assert connected["connection"]["connected"] is True
    assert connected["connection"]["transport"] == "mock"
    assert status_after["connected"] is True
    assert status_after["healthy"] is True
    assert disconnected == {"connected": False, "transport": "mock"}

    public_payload = json.dumps(
        {
            "status_before": status_before,
            "connected": connected,
            "status_after": status_after,
            "disconnected": disconnected,
        },
        sort_keys=True,
    )
    assert secret not in public_payload
    assert "auth_token" not in public_payload


def test_unreal_mcp_execute_route_runs_readonly_command() -> None:
    manager = _mock_manager()
    request = _request_for(manager)

    async def execute_ping() -> dict[str, object]:
        await connect(request)
        return await execute(request, MCPExecuteRequest(name="unreal.ping"))

    try:
        response = asyncio.run(execute_ping())
    finally:
        asyncio.run(manager.stop())

    assert response["result"]["success"] is True
    assert response["result"]["data"] == {"message": "pong"}


def test_unreal_mcp_execute_route_rejects_disabled_write_command() -> None:
    manager = _mock_manager()
    request = _request_for(manager)

    async def execute_write_command() -> None:
        await connect(request)
        await execute(
            request,
            MCPExecuteRequest(
                name="unreal.open_map",
                arguments={"map_path": "/Game/Maps/L_PineRoad"},
            ),
        )

    try:
        try:
            asyncio.run(execute_write_command())
        except HTTPException as error:
            assert error.status_code == 403
            assert error.detail["code"] == "mcp_permission_error"
        else:
            raise AssertionError("Expected disabled write command to raise HTTPException")
    finally:
        asyncio.run(manager.stop())
