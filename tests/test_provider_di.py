import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.core.di import create_app_container


def test_container_wires_provider_layer() -> None:
    container = create_app_container()
    try:
        assert container.provider_registry is not None
        assert container.provider_factory is not None
        assert container.provider_manager is not None
        assert container.provider_manager.get_active_provider().name == "mock"
    finally:
        assert container.runtime is not None
        container.runtime.shutdown()


def test_application_registers_provider_manager_in_runtime() -> None:
    from backend.app.main import app

    runtime = app.state.runtime
    try:
        assert app.state.container.provider_manager is not None
        assert runtime.get_service("ai_provider_manager") is app.state.container.provider_manager
    finally:
        runtime.shutdown()
