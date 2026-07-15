import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.providers.errors import (
    ProviderConfigurationError,
    ProviderNotFoundError,
    ProviderUnavailableError,
)
from backend.providers.factory import ProviderFactory
from backend.providers.manager import ProviderManager
from backend.providers.mock_provider import MockProvider
from backend.providers.models import GenerationRequest
from backend.providers.registry import ProviderRegistry


def test_mock_provider_returns_deterministic_response_and_metadata() -> None:
    provider = MockProvider()
    request = GenerationRequest(prompt="Create a misty pine road")

    response = provider.generate(request)

    assert response.content == "Mock response: Create a misty pine road"
    assert response.provider_name == "mock"
    assert response.model == "mock-model"
    assert response.metadata == {"mode": "offline", "request_count": 1}
    assert provider.requests == [request]
    assert provider.get_info().to_dict()["capabilities"]["text_generation"] is True


def test_registry_resolves_providers_and_reports_missing_names() -> None:
    registry = ProviderRegistry()
    provider = MockProvider()
    registry.register(provider)

    assert registry.get("mock") is provider
    assert registry.list_providers() == [provider]

    try:
        registry.get("missing")
    except ProviderNotFoundError as error:
        assert error.provider_name == "missing"
    else:
        raise AssertionError("Expected ProviderNotFoundError")


def test_factory_builds_and_registers_supported_provider() -> None:
    registry = ProviderRegistry()
    factory = ProviderFactory(registry=registry)
    factory.register_builder("mock", MockProvider)

    provider = factory.create_provider("mock")

    assert isinstance(provider, MockProvider)
    assert registry.get("mock") is provider

    try:
        factory.create_provider("unsupported")
    except ProviderConfigurationError as error:
        assert "unsupported" in str(error)
    else:
        raise AssertionError("Expected ProviderConfigurationError")


def test_manager_delegates_to_active_provider() -> None:
    registry = ProviderRegistry()
    provider = MockProvider()
    registry.register(provider)
    manager = ProviderManager(registry=registry)
    manager.set_active_provider("mock")

    response = manager.generate(GenerationRequest(prompt="Generate terrain"))

    assert response.content == "Mock response: Generate terrain"
    assert manager.get_active_provider_info().name == "mock"


def test_manager_rejects_unavailable_provider() -> None:
    registry = ProviderRegistry()
    registry.register(MockProvider(available=False))
    manager = ProviderManager(registry=registry)
    manager.set_active_provider("mock")

    try:
        manager.generate(GenerationRequest(prompt="Generate terrain"))
    except ProviderUnavailableError as error:
        assert error.provider_name == "mock"
    else:
        raise AssertionError("Expected ProviderUnavailableError")
