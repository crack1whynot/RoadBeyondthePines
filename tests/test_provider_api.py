import sys
from pathlib import Path
from types import SimpleNamespace

from fastapi import HTTPException

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.api.routes.providers import generate, get_active_provider, list_providers
from backend.providers.manager import ProviderManager
from backend.providers.mock_provider import MockProvider
from backend.providers.models import GenerationRequest
from backend.providers.registry import ProviderRegistry


def _request_for(manager: ProviderManager | None) -> SimpleNamespace:
    container = SimpleNamespace(provider_manager=manager)
    app = SimpleNamespace(state=SimpleNamespace(container=container))
    return SimpleNamespace(app=app)


def _manager(*, available: bool = True) -> ProviderManager:
    registry = ProviderRegistry()
    registry.register(MockProvider(available=available))
    manager = ProviderManager(registry=registry)
    manager.set_active_provider("mock")
    return manager


def test_provider_routes_list_active_provider_and_generate() -> None:
    request = _request_for(_manager())

    providers = list_providers(request)
    active = get_active_provider(request)
    generated = generate(request, GenerationRequest(prompt="Create a forest"))

    assert providers["providers"][0]["name"] == "mock"
    assert active["provider"]["name"] == "mock"
    assert generated["response"]["content"] == "Mock response: Create a forest"


def test_generate_route_maps_missing_provider_to_not_found() -> None:
    request = _request_for(_manager())

    try:
        generate(request, GenerationRequest(prompt="Create a forest"), provider_name="missing")
    except HTTPException as error:
        assert error.status_code == 404
    else:
        raise AssertionError("Expected HTTPException")


def test_generate_route_maps_unavailable_provider_to_service_unavailable() -> None:
    request = _request_for(_manager(available=False))

    try:
        generate(request, GenerationRequest(prompt="Create a forest"))
    except HTTPException as error:
        assert error.status_code == 503
    else:
        raise AssertionError("Expected HTTPException")


def test_provider_routes_report_uninitialized_container() -> None:
    request = _request_for(None)

    try:
        list_providers(request)
    except HTTPException as error:
        assert error.status_code == 503
    else:
        raise AssertionError("Expected HTTPException")
