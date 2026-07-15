from __future__ import annotations

from abc import ABC, abstractmethod

from backend.providers.models import GenerationRequest, GenerationResponse, ProviderInfo


class AIProvider(ABC):
    """Canonical synchronous contract for provider implementations."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the stable name used to register this provider."""
        raise NotImplementedError

    @abstractmethod
    def get_info(self) -> ProviderInfo:
        """Return public metadata without exposing configuration secrets."""
        raise NotImplementedError

    @abstractmethod
    def is_available(self) -> bool:
        """Report whether the provider can currently serve requests."""
        raise NotImplementedError

    @abstractmethod
    def generate(self, request: GenerationRequest) -> GenerationResponse:
        """Generate a response for a provider-independent request."""
        raise NotImplementedError
