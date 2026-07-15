import sys
from pathlib import Path

from fastapi.testclient import TestClient

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
    from backend.app.main import create_app

    app = create_app()
    # The composition root is now constructed by FastAPI lifespan rather than
    # at import time, so inspect it inside a real ASGI lifecycle.
    with TestClient(app):
        runtime = app.state.runtime
        assert app.state.container.provider_manager is not None
        assert runtime.get_service("ai_provider_manager") is app.state.container.provider_manager
