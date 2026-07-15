from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace
from urllib import error as urllib_error
from urllib import request as urllib_request

import pytest
from fastapi.exceptions import RequestValidationError
from starlette.requests import Request

from backend.app.main import application_lifespan, validation_exception_handler
from backend.mcp.client import UnrealMCPClient
from backend.mcp.errors import (
    MCPCommandRejectedError,
    MCPInvalidRequestError,
    MCPPermissionError,
)
from backend.mcp.mock_transport import MockUnrealTransport
from backend.mcp.models import (
    MCPCommand,
    MCPCommandResult,
    MCPErrorInfo,
    MCPHealthStatus,
    UnrealConnectionInfo,
)
from backend.mcp.security import MCPSecurityPolicy
from backend.mcp.transport import UnrealTransport
from backend.mcp.transports.http_transport import _NoRedirectHandler


_REJECTED_COMMAND_ERRORS = (
    MCPCommandRejectedError,
    MCPInvalidRequestError,
    MCPPermissionError,
)


class _RecordingTransport(UnrealTransport):
    """Connected test double that records only commands reaching the transport."""

    def __init__(self) -> None:
        self.connected = False
        self.executed_commands: list[MCPCommand] = []

    async def connect(self) -> UnrealConnectionInfo:
        self.connected = True
        return UnrealConnectionInfo(connected=True, transport=self.get_name())

    async def disconnect(self) -> None:
        self.connected = False

    async def is_connected(self) -> bool:
        return self.connected

    async def execute(self, command: MCPCommand) -> MCPCommandResult:
        self.executed_commands.append(command)
        return MCPCommandResult(command_id=command.id, success=True, data={"ok": True})

    async def health_check(self) -> MCPHealthStatus:
        return MCPHealthStatus(healthy=self.connected, connected=self.connected)

    def get_name(self) -> str:
        return "recording"


def test_public_mcp_models_redact_bearer_and_credential_values() -> None:
    secret = "unreal-mcp-regression-secret"
    stack_trace = "Stack trace: File C:/GameDevelopment/bridge.py, line 12"
    result = MCPCommandResult(
        command_id="security-result",
        success=True,
        data={
            "message": f"Bearer {secret}",
            "credential": secret,
            "nested": {"access_token": secret},
        },
    )
    health = MCPHealthStatus(
        healthy=False,
        connected=False,
        message=f"Bridge denied Bearer {secret}",
        details={"credential": secret, "token": secret},
    )
    error = MCPErrorInfo(
        code="mcp_transport_error",
        message=f"Bridge denied Bearer {secret}",
        details={"credential": secret, "token": secret},
    )
    trace_result = MCPCommandResult(
        command_id="security-trace-result",
        success=True,
        data=stack_trace,
    )

    public_payload = json.dumps(
        {
            "result": result.to_dict(),
            "health": health.to_dict(),
            "error": error.to_dict(),
            "trace_result": trace_result.to_dict(),
        },
        sort_keys=True,
    )

    assert secret not in public_payload
    assert f"Bearer {secret}" not in public_payload
    assert stack_trace not in public_payload


def test_policy_and_client_reject_native_paths_and_unexpected_arguments_before_transport() -> None:
    commands = (
        MCPCommand(
            name="unreal.list_assets",
            arguments={"path": r"C:\\Unreal\\Content"},
        ),
        MCPCommand(
            name="unreal.get_asset",
            arguments={"object_path": "/tmp/private.uasset"},
        ),
        MCPCommand(
            name="unreal.list_assets",
            arguments={"path": "/Game", "unexpected": "not allowed"},
        ),
        MCPCommand(
            name="unreal.list_assets",
            arguments={"path": "/Game", "shell": "powershell -Command dir"},
        ),
    )
    policy = MCPSecurityPolicy()

    for command in commands:
        with pytest.raises(_REJECTED_COMMAND_ERRORS):
            policy.validate(command)

    async def scenario() -> None:
        transport = _RecordingTransport()
        client = UnrealMCPClient(transport, security_policy=policy)
        await client.connect()

        for command in commands:
            with pytest.raises(_REJECTED_COMMAND_ERRORS):
                await client.execute(command)

        assert transport.executed_commands == []

    asyncio.run(scenario())


def test_open_map_requires_write_permission_confirmation_and_safe_target() -> None:
    safe_map_path = "/Game/Maps/L_PineRoad"
    command = MCPCommand(
        name="unreal.open_map",
        arguments={"map_path": safe_map_path, "confirm_write": True},
        read_only=False,
    )

    with pytest.raises(MCPPermissionError):
        MCPSecurityPolicy().validate(command)

    write_policy = MCPSecurityPolicy(allow_write=True)
    for arguments in (
        {"confirm_write": True},
        {"map_path": r"C:\\Unreal\\Content\\Secret", "confirm_write": True},
        {"map_path": "../OutsideProject", "confirm_write": True},
        {
            "map_path": safe_map_path,
            "confirm_write": True,
            "unexpected": "not allowed",
        },
    ):
        with pytest.raises(_REJECTED_COMMAND_ERRORS):
            write_policy.validate(
                MCPCommand(name="unreal.open_map", arguments=arguments, read_only=False)
            )

    definition = write_policy.validate(command)
    assert definition.name == "unreal.open_map"


def test_validation_handler_never_returns_raw_invalid_input_or_token() -> None:
    secret = "unreal-validation-secret"
    request = Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/unreal-mcp/execute",
            "headers": [],
        }
    )
    validation_error = RequestValidationError(
        [
            {
                "type": "string_type",
                "loc": ("body", "arguments", "authorization"),
                "msg": "Input should be a valid string",
                "input": f"Bearer {secret}",
            }
        ]
    )

    response = asyncio.run(validation_exception_handler(request, validation_error))
    response_body = response.body.decode("utf-8")

    assert response.status_code == 422
    assert secret not in response_body
    assert f"Bearer {secret}" not in response_body
    assert '"input"' not in response_body


def test_client_health_check_keeps_connection_cache_aligned_with_transport_health() -> None:
    async def scenario() -> None:
        transport = MockUnrealTransport()
        client = UnrealMCPClient(transport)
        await client.connect()
        await transport.disconnect()

        health = await client.health_check()

        assert health.connected is False
        assert client.connection_info.connected is health.connected

    asyncio.run(scenario())


def test_http_redirect_handler_rejects_redirect_before_authorization_can_forward() -> None:
    handler = _NoRedirectHandler()
    request = urllib_request.Request(
        "http://bridge.test/connection",
        headers={"Authorization": "Bearer never-forward-this"},
    )

    with pytest.raises(urllib_error.HTTPError) as error:
        handler.redirect_request(
            request,
            None,
            302,
            "Found",
            {"Location": "https://other.example/connection"},
            "https://other.example/connection",
        )

    assert error.value.code == 302
    assert "other.example" not in str(error.value)


def test_application_lifespan_starts_and_stops_mcp_before_runtime_shutdown() -> None:
    events: list[str] = []

    class _LifecycleManager:
        async def start(self) -> None:
            events.append("manager.start")

        async def stop(self) -> None:
            events.append("manager.stop")

    class _Runtime:
        def shutdown(self) -> None:
            events.append("runtime.shutdown")

    application = SimpleNamespace(
        state=SimpleNamespace(
            unreal_mcp_manager=_LifecycleManager(),
            runtime=_Runtime(),
        )
    )

    async def scenario() -> None:
        async with application_lifespan(application):
            assert events == ["manager.start"]

    asyncio.run(scenario())

    assert events == ["manager.start", "manager.stop", "runtime.shutdown"]
