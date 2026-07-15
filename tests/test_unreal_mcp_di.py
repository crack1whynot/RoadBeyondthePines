import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.core.config import Settings
from backend.core.di import create_app_container


def _mock_settings(*, auto_connect: bool = False) -> Settings:
    return Settings(
        unreal_mcp_transport="mock",
        unreal_mcp_auto_connect=auto_connect,
        unreal_mcp_allow_write=False,
    )


def test_container_registers_mock_unreal_mcp_manager_in_runtime() -> None:
    container = create_app_container(_mock_settings())
    try:
        assert container.runtime is not None
        assert container.unreal_transport_registry is not None
        assert container.unreal_transport_registry.list_names() == ["http", "mock"]
        assert container.unreal_mcp_manager is not None
        assert container.unreal_service is not None
        assert container.runtime.get_service("unreal_mcp_manager") is container.unreal_mcp_manager
        assert container.unreal_service.status()["transport"] == "mock"
        assert container.unreal_mcp_manager.get_connection_state().connected is False
    finally:
        if container.unreal_mcp_manager is not None:
            asyncio.run(container.unreal_mcp_manager.stop())
        assert container.runtime is not None
        container.runtime.shutdown()


def test_mock_manager_start_and_stop_are_safe_through_fresh_container() -> None:
    container = create_app_container(_mock_settings(auto_connect=True))
    assert container.unreal_mcp_manager is not None
    manager = container.unreal_mcp_manager

    async def exercise_lifecycle() -> tuple[bool, bool]:
        await manager.start()
        connected_after_start = manager.get_connection_state().connected
        await manager.start()
        await manager.stop()
        connected_after_stop = manager.get_connection_state().connected
        await manager.stop()
        return connected_after_start, connected_after_stop

    try:
        connected_after_start, connected_after_stop = asyncio.run(exercise_lifecycle())
    finally:
        asyncio.run(manager.stop())
        assert container.runtime is not None
        container.runtime.shutdown()

    assert connected_after_start is True
    assert connected_after_stop is False
