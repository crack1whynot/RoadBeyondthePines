from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from backend.providers.base import AIProvider
from backend.providers.errors import ProviderConfigurationError
from backend.providers.registry import ProviderRegistry

ProviderBuilder = Callable[[], AIProvider]


@dataclass(slots=True)
class ProviderFactory:
    """Builds supported providers and optionally registers their instances."""

    registry: ProviderRegistry | None = None
    builders: dict[str, ProviderBuilder] = field(default_factory=dict)

    def register_builder(self, provider_name: str, builder: ProviderBuilder) -> None:
        """Register a constructor for a supported provider type."""
        self.builders[provider_name] = builder

    def create_provider(self, provider_name: str) -> AIProvider:
        """Create a configured provider and add it to the attached registry."""
        builder = self.builders.get(provider_name)
        if builder is None:
            raise ProviderConfigurationError(f"Unsupported AI provider '{provider_name}'")

        provider = builder()
        if self.registry is not None:
            self.registry.register(provider)
        return provider
