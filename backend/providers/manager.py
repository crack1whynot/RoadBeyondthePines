from __future__ import annotations

from dataclasses import dataclass

from backend.providers.base import AIProvider
from backend.providers.errors import ProviderConfigurationError, ProviderUnavailableError
from backend.providers.models import GenerationRequest, GenerationResponse, ProviderInfo
from backend.providers.registry import ProviderRegistry


@dataclass(slots=True)
class ProviderManager:
    """Selects registered providers and delegates generation requests."""

    registry: ProviderRegistry
    active_provider_name: str | None = None

    def set_active_provider(self, provider_name: str) -> AIProvider:
        """Select an already registered provider as the default provider."""
        provider = self.registry.get(provider_name)
        self.active_provider_name = provider.name
        return provider

    def get_active_provider(self) -> AIProvider:
        """Return the configured default provider."""
        if self.active_provider_name is None:
            raise ProviderConfigurationError("No active AI provider is configured")
        return self.registry.get(self.active_provider_name)

    def list_provider_info(self) -> list[ProviderInfo]:
        """Return public metadata for each registered provider."""
        return [provider.get_info() for provider in self.registry.list_providers()]

    def get_active_provider_info(self) -> ProviderInfo:
        """Return public metadata for the active provider."""
        return self.get_active_provider().get_info()

    def generate(
        self,
        request: GenerationRequest,
        provider_name: str | None = None,
    ) -> GenerationResponse:
        """Generate through the selected provider or the configured default."""
        provider = (
            self.registry.get(provider_name)
            if provider_name is not None
            else self.get_active_provider()
        )
        if not provider.is_available():
            raise ProviderUnavailableError(provider.name)
        return provider.generate(request)
