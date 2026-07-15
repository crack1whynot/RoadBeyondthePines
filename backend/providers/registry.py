from __future__ import annotations

from dataclasses import dataclass, field

from backend.providers.base import AIProvider
from backend.providers.errors import ProviderNotFoundError


@dataclass(slots=True)
class ProviderRegistry:
    """In-memory registry of configured AI provider instances."""

    providers: dict[str, AIProvider] = field(default_factory=dict)

    def register(self, provider: AIProvider) -> None:
        """Register or replace a provider under its stable name."""
        self.providers[provider.name] = provider

    def unregister(self, provider_name: str) -> None:
        """Remove a provider if it is registered."""
        self.providers.pop(provider_name, None)

    def get(self, provider_name: str) -> AIProvider:
        """Return a provider or raise a domain-specific lookup error."""
        provider = self.providers.get(provider_name)
        if provider is None:
            raise ProviderNotFoundError(provider_name)
        return provider

    def list_providers(self) -> list[AIProvider]:
        """Return registered providers in deterministic name order."""
        return [self.providers[name] for name in sorted(self.providers)]
