from __future__ import annotations

import asyncio
import json

import pytest

from backend.mcp.client import UnrealMCPClient
from backend.mcp.errors import (
    MCPCommandNotFoundError,
    MCPInvalidRequestError,
    MCPNotConnectedError,
    MCPPermissionError,
    MCPTimeoutError,
    MCPTransportError,
)
from backend.mcp.manager import UnrealMCPManager
from backend.mcp.mock_transport import MockUnrealTransport
from backend.mcp.models import (
    MCPCommand,
    MCPCommandResult,
    MCPHealthStatus,
    UnrealConnectionInfo,
)
from backend.mcp.registry import UnrealTransportRegistry
from backend.mcp.security import MCPSecurityPolicy
from backend.mcp.transport import UnrealTransport
from backend.mcp.transports.http_transport import HTTPRequest, HTTPResponse, HTTPUnrealTransport


class _TinyUnrealTransport(UnrealTransport):
    """Small controllable transport used to test client-only behavior."""

    def __init__(self, mode: str = "success") -> None:
        self.mode = mode
        self.connected = False

    async def connect(self) -> UnrealConnectionInfo:
        self.connected = True
        return UnrealConnectionInfo(connected=True, transport=self.get_name())

    async def disconnect(self) -> None:
        self.connected = False

    async def is_connected(self) -> bool:
        return self.connected

    async def execute(self, command: MCPCommand) -> MCPCommandResult:
        if self.mode == "timeout":
            await asyncio.sleep(0.05)
        if self.mode == "failure":
            raise RuntimeError("internal fake transport failure")
        return MCPCommandResult(
            command_id=command.id,
            success=True,
            data={"command": command.name},
        )

    async def health_check(self) -> MCPHealthStatus:
        return MCPHealthStatus(healthy=self.connected, connected=self.connected)

    def get_name(self) -> str:
        return "tiny"


def test_mock_transport_connect_disconnect_and_health() -> None:
    async def scenario() -> None:
        transport = MockUnrealTransport()

        before_connect = await transport.health_check()
        assert before_connect.healthy is False
        assert before_connect.connected is False

        connection = await transport.connect()
        assert connection.connected is True
        assert connection.transport == "mock"
        assert connection.project_name == "RoadBeyondThePines"
        assert await transport.is_connected() is True

        healthy = await transport.health_check()
        assert healthy.healthy is True
        assert healthy.connected is True
        assert healthy.latency_ms == 0.0

        await transport.disconnect()
        assert await transport.is_connected() is False
        after_disconnect = await transport.health_check()
        assert after_disconnect.healthy is False
        assert after_disconnect.connected is False

    asyncio.run(scenario())


def test_mock_transport_read_only_commands_return_stable_data() -> None:
    async def scenario() -> None:
        client = UnrealMCPClient(MockUnrealTransport())
        await client.connect()

        ping = await client.ping()
        project = await client.get_project_info()
        maps = await client.list_maps()
        assets = await client.list_assets(class_name="StaticMesh", limit=1)
        asset = await client.get_asset(
            "/Game/Environment/PineTrees/SM_PineTree_01.SM_PineTree_01"
        )

        assert ping.data == {"message": "pong"}
        assert project.data["project_name"] == "RoadBeyondThePines"
        assert project.data["engine_version"] == "5.8"
        assert [item["name"] for item in maps.data["maps"]] == [
            "L_PineRoad",
            "L_ForestOutpost",
            "L_Prototype",
        ]
        assert assets.data["total"] == 1
        assert assets.data["assets"][0]["asset_class"] == "StaticMesh"
        assert asset.data["asset_name"] == "SM_PineTree_01"

    asyncio.run(scenario())


def test_unknown_command_is_rejected_before_mock_execution() -> None:
    async def scenario() -> None:
        client = UnrealMCPClient(MockUnrealTransport())
        await client.connect()

        with pytest.raises(MCPCommandNotFoundError):
            await client.execute(MCPCommand(name="unreal.not_a_command"))

    asyncio.run(scenario())


def test_write_command_requires_explicit_policy_and_confirmation() -> None:
    async def scenario() -> None:
        blocked_client = UnrealMCPClient(MockUnrealTransport())
        await blocked_client.connect()
        with pytest.raises(MCPPermissionError):
            await blocked_client.execute(
                MCPCommand(
                    name="unreal.open_map",
                    arguments={"map_path": "L_PineRoad", "confirm_write": True},
                    read_only=False,
                )
            )

        allowed_client = UnrealMCPClient(
            MockUnrealTransport(),
            security_policy=MCPSecurityPolicy(allow_write=True),
        )
        await allowed_client.connect()
        with pytest.raises(MCPPermissionError):
            await allowed_client.execute(
                MCPCommand(
                    name="unreal.open_map",
                    arguments={"map_path": "L_PineRoad"},
                    read_only=False,
                )
            )

        result = await allowed_client.execute(
            MCPCommand(
                name="unreal.open_map",
                arguments={"map_path": "L_PineRoad", "confirm_write": True},
                read_only=False,
            )
        )
        assert result.success is True
        assert result.data["opened_map"]["name"] == "L_PineRoad"
        assert result.data["simulated"] is True

    asyncio.run(scenario())


def test_disconnected_client_rejects_execution() -> None:
    async def scenario() -> None:
        client = UnrealMCPClient(MockUnrealTransport())

        with pytest.raises(MCPNotConnectedError):
            await client.ping()

    asyncio.run(scenario())


def test_manager_start_auto_connect_and_stop() -> None:
    async def scenario() -> None:
        transport = MockUnrealTransport()
        manager = UnrealMCPManager(UnrealMCPClient(transport), auto_connect=True)

        await manager.start()
        assert manager.get_connection_state().connected is True
        assert await transport.is_connected() is True

        await manager.stop()
        assert manager.get_connection_state().connected is False
        assert await transport.is_connected() is False

    asyncio.run(scenario())


def test_transport_registry_requires_explicit_replace() -> None:
    registry = UnrealTransportRegistry()
    original_builder = lambda _: MockUnrealTransport()
    replacement_builder = lambda _: MockUnrealTransport(project_path="C:/Replacement")
    registry.register("mock", original_builder)

    with pytest.raises(MCPInvalidRequestError):
        registry.register("mock", replacement_builder)

    registry.register("MOCK", replacement_builder, replace=True)
    assert registry.get("mock") is replacement_builder
    assert registry.list_names() == ["mock"]


def test_client_normalizes_timeout_and_unexpected_transport_error() -> None:
    async def scenario() -> None:
        timeout_client = UnrealMCPClient(
            _TinyUnrealTransport(mode="timeout"),
            default_timeout_seconds=0.001,
        )
        await timeout_client.connect()
        with pytest.raises(MCPTimeoutError) as timeout_error:
            await timeout_client.ping()
        assert timeout_error.value.details == {"operation": "command execution"}

        failing_client = UnrealMCPClient(_TinyUnrealTransport(mode="failure"))
        await failing_client.connect()
        with pytest.raises(MCPTransportError) as transport_error:
            await failing_client.ping()
        assert transport_error.value.details == {"operation": "command execution"}

    asyncio.run(scenario())


def test_http_transport_accepts_an_injected_sender_without_network() -> None:
    async def scenario() -> None:
        requests: list[HTTPRequest] = []

        def sender(request: HTTPRequest) -> HTTPResponse:
            requests.append(request)
            if request.url == "http://bridge.test/connection":
                return HTTPResponse(
                    status=200,
                    body={
                        "connected": True,
                        "transport": "http",
                        "project_name": "InjectedBridgeProject",
                        "capabilities": ["project.read"],
                    },
                )
            if request.url == "http://bridge.test/health":
                return HTTPResponse(
                    status=200,
                    body={"healthy": True, "connected": True, "latency_ms": 0.0},
                )
            if request.url == "http://bridge.test/commands":
                payload = json.loads((request.body or b"{}").decode("utf-8"))
                return HTTPResponse(
                    status=200,
                    body={
                        "command_id": payload["id"],
                        "success": True,
                        "data": {"message": "pong"},
                    },
                )
            raise AssertionError(f"Unexpected fake bridge request: {request.url}")

        transport = HTTPUnrealTransport(base_url="http://bridge.test", sender=sender)
        client = UnrealMCPClient(transport)

        connection = await client.connect()
        health = await client.health_check()
        result = await client.ping()
        await client.disconnect()

        assert connection.project_name == "InjectedBridgeProject"
        assert health.healthy is True
        assert result.data == {"message": "pong"}
        assert [(request.method, request.url) for request in requests] == [
            ("GET", "http://bridge.test/connection"),
            ("GET", "http://bridge.test/health"),
            ("POST", "http://bridge.test/commands"),
        ]

    asyncio.run(scenario())
