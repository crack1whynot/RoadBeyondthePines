"""Provider-neutral AI integration contracts and implementations."""

from backend.providers.base import AIProvider
from backend.providers.errors import (
    ProviderConfigurationError,
    ProviderError,
    ProviderGenerationError,
    ProviderNotFoundError,
    ProviderUnavailableError,
)
from backend.providers.models import (
    GenerationRequest,
    GenerationResponse,
    ProviderCapabilities,
    ProviderInfo,
)
from backend.providers.factory import ProviderFactory
from backend.providers.manager import ProviderManager
from backend.providers.mock_provider import MockProvider
from backend.providers.registry import ProviderRegistry

__all__ = [
    "AIProvider",
    "GenerationRequest",
    "GenerationResponse",
    "MockProvider",
    "ProviderCapabilities",
    "ProviderConfigurationError",
    "ProviderError",
    "ProviderGenerationError",
    "ProviderInfo",
    "ProviderFactory",
    "ProviderManager",
    "ProviderNotFoundError",
    "ProviderRegistry",
    "ProviderUnavailableError",
]
