from __future__ import annotations


class ProviderError(Exception):
    """Base error for the AI Providers layer."""


class ProviderConfigurationError(ProviderError):
    """Raised when a provider cannot be created from configuration."""


class ProviderNotFoundError(ProviderError):
    """Raised when a requested provider is not registered."""

    def __init__(self, provider_name: str) -> None:
        super().__init__(f"AI provider '{provider_name}' is not registered")
        self.provider_name = provider_name


class ProviderUnavailableError(ProviderError):
    """Raised when a registered provider is not currently available."""

    def __init__(self, provider_name: str) -> None:
        super().__init__(f"AI provider '{provider_name}' is unavailable")
        self.provider_name = provider_name


class ProviderGenerationError(ProviderError):
    """Raised when a provider fails to generate a response."""
