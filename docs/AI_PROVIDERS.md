# AI Provider Layer

## Purpose

The AI Provider Layer is the provider-neutral boundary for text generation in
Road Beyond the Pines Studio. It keeps provider selection, provider metadata,
and generation requests separate from Runtime, Brain, Memory, and the Agent
System.

The layer currently ships with one deterministic, offline implementation:
`MockProvider`. It is intended for local development and tests; it does not
call an external AI service.

The code uses the following concrete names:

- an AI request is `GenerationRequest`;
- an AI response is `GenerationResponse`;
- the provider manager is `ProviderManager`;
- the mock provider is `MockProvider`.

There are no classes named `AIRequest`, `AIResponse`, `AIProviderManager`, or
`MockAIProvider` in the current codebase.

## Architecture

```text
Settings.ai_provider
        |
        v
ProviderFactory -> ProviderRegistry -> ProviderManager
                                        |
                                        v
GenerationRequest -> AIProvider.generate() -> GenerationResponse
```

During FastAPI lifespan startup, `backend/app/main.py` calls
`create_app_container()` in `backend/core/di.py`. The composition root
registers supported provider builders, creates the configured provider,
registers the created instance, and selects it as the active provider. The
composition root (not the route layer or `main.py`) registers the manager in
the Runtime Service Registry as `"ai_provider_manager"` for compatibility
lookup.

The HTTP routes use `request.app.state.container.provider_manager`. They do
not import or construct a concrete provider themselves.

The older `backend/integrations/ai_provider.py` is a separate, unused legacy
abstraction. It is not the contract used by this layer.

## Files and classes

| File | Main contents | Responsibility |
| --- | --- | --- |
| `backend/providers/models.py` | `GenerationRequest`, `GenerationResponse`, `ProviderInfo`, `ProviderCapabilities` | Provider-neutral data contracts and safe public metadata. |
| `backend/providers/base.py` | `AIProvider` | Synchronous abstract provider contract. |
| `backend/providers/errors.py` | `ProviderError` and provider-specific errors | Domain errors for configuration, lookup, availability, and generation. |
| `backend/providers/registry.py` | `ProviderRegistry` | In-memory registration, lookup, removal, and deterministic listing of provider instances. |
| `backend/providers/factory.py` | `ProviderFactory` | Registers provider constructors and creates configured instances. |
| `backend/providers/manager.py` | `ProviderManager` | Stores the active provider selection and delegates generation. |
| `backend/providers/mock_provider.py` | `MockProvider` | Deterministic offline implementation. |
| `backend/api/routes/providers.py` | Providers router | Public API for discovery, active-provider metadata, and generation. |

### `AIProvider`

Every provider implementation must supply these synchronous members:

- `name`: its stable registry name;
- `get_info() -> ProviderInfo`: public, non-secret metadata;
- `is_available() -> bool`: current availability;
- `generate(request: GenerationRequest) -> GenerationResponse`.

### Request and response models

`GenerationRequest` requires `prompt`. It also accepts optional
`system_prompt`, `model`, `temperature`, `max_tokens`, and free-form
`metadata`.

`GenerationResponse` contains `content`, `provider_name`, optional `model`,
`finish_reason` (default: `"stop"`), and free-form `metadata`.

## Request lifecycle

The request flow is synchronous:

```text
GenerationRequest
  -> ProviderManager.generate(...)
  -> selected AIProvider
  -> AIProvider.generate(request)
  -> GenerationResponse
```

`ProviderManager.generate()` chooses a provider in this order:

1. If its `provider_name` argument is supplied, it resolves that exact name
   from `ProviderRegistry`.
2. Otherwise, it resolves the manager's active provider.
3. It calls `is_available()`. An unavailable provider raises
   `ProviderUnavailableError`.
4. It delegates to that provider's `generate()` method.

For HTTP traffic, `POST /providers/generate` converts the returned response
to a JSON object under the `response` key.

## `MockProvider`

`MockProvider` is the only built-in provider in this stage. Its stable name is
`mock`, its default model name is `mock-model`, and it reports the metadata
`{"mode": "offline"}`.

For a prompt such as `Create a forest`, it returns:

```text
Mock response: Create a forest
```

It stores received `GenerationRequest` objects in its in-memory `requests`
list. Its `available` constructor field defaults to `True`; if it is `False`,
both the manager and the provider reject generation with
`ProviderUnavailableError`.

## Provider Registry and Manager

`ProviderRegistry` is an in-memory dictionary keyed by `AIProvider.name`.
Registering a second provider with the same name replaces the first one.
`get()` raises `ProviderNotFoundError` for an unknown name, while
`list_providers()` returns providers sorted by name.

`ProviderManager` owns the selected active provider name. It provides:

- `set_active_provider()` to select an already registered provider;
- `get_active_provider()` and `get_active_provider_info()`;
- `list_provider_info()`;
- `generate()` to select and call a provider.

There is no API endpoint for changing the active provider at runtime. The
application selects it during DI construction from `AI_PROVIDER`.

## Default provider, fallback, and failures

`AI_PROVIDER=mock` is the default and the value in `.env.example`. During
startup, the DI container registers the `mock` builder and constructs a
`MockProvider`.

For backward compatibility, the DI container also registers a factory builder
named `placeholder`. Selecting `AI_PROVIDER=placeholder` still constructs a
`MockProvider`; its registered and active provider name remains `mock`.
`placeholder` is therefore a startup-only factory alias, not a second
registry name and not a valid `provider_name=placeholder` API selection.

There is **no automatic fallback chain**. In particular:

- an unknown explicit `provider_name` raises `ProviderNotFoundError`;
- an unavailable provider raises `ProviderUnavailableError`;
- no provider is selected when there is no active name, which raises
  `ProviderConfigurationError`;
- an unsupported `AI_PROVIDER` value raises `ProviderConfigurationError`
  while the application container is being created.

The API maps known provider errors to HTTP 404 (unknown provider), 503
(configuration or availability), and 502 (`ProviderGenerationError`). The
current `MockProvider` does not raise `ProviderGenerationError`.

## Environment variables and API keys

The only AI-provider-specific setting currently supported by
`backend/core/config.py` is:

```dotenv
AI_PROVIDER=mock
```

`Settings` reads `.env` case-insensitively. `.env.example` contains no API
keys and no SDK-specific settings; it contains only variables supported by
the current `Settings` model.

No API key, endpoint URL, model selector, or provider SDK configuration is
implemented in this stage. The provider layer does not read, persist, log, or
send an API key. The repository's `.gitignore` excludes `.env` and
`.env.local`; secrets must never be committed or added to `.env.example`.

When a future provider needs a key, it should read it from a private
environment file or a deployment secret store, keep it out of public API
responses (including `/settings`), and document the new supported setting at
the same time.

## Missing SDKs or keys

The bundled `MockProvider` needs neither an SDK nor an API key, so it remains
usable offline. There is no concrete remote provider in the repository and no
generic missing-SDK or missing-key recovery path.

If `AI_PROVIDER` names an unsupported provider, factory construction fails
with `ProviderConfigurationError` during application startup. If a future
registered provider reports itself unavailable, the manager returns
`ProviderUnavailableError`; it does not switch to `MockProvider`.

## Adding a provider

1. Implement `AIProvider` using the existing request and response models.
2. Register a zero-argument builder with `ProviderFactory` in the composition
   root before `create_provider(settings.ai_provider)` is called.
3. Set `AI_PROVIDER` to the builder's registered name.
4. Add isolated tests for metadata, availability, success, and expected
   provider errors.

Minimal provider shape:

```python
from backend.providers.base import AIProvider
from backend.providers.models import (
    GenerationRequest,
    GenerationResponse,
    ProviderInfo,
)


class ExampleProvider(AIProvider):
    @property
    def name(self) -> str:
        return "example"

    def get_info(self) -> ProviderInfo:
        return ProviderInfo(name=self.name, display_name="Example Provider")

    def is_available(self) -> bool:
        return True

    def generate(self, request: GenerationRequest) -> GenerationResponse:
        return GenerationResponse(
            content=request.prompt,
            provider_name=self.name,
        )
```

The corresponding builder registration is:

```python
provider_factory.register_builder("example", ExampleProvider)
```

## Python example

```python
from backend.providers.manager import ProviderManager
from backend.providers.mock_provider import MockProvider
from backend.providers.models import GenerationRequest
from backend.providers.registry import ProviderRegistry

registry = ProviderRegistry()
registry.register(MockProvider())

manager = ProviderManager(registry=registry)
manager.set_active_provider("mock")

response = manager.generate(GenerationRequest(prompt="Create a forest"))
print(response.content)  # Mock response: Create a forest
```

## HTTP API example

```bash
curl -X POST "http://127.0.0.1:8000/providers/generate" \
  -H "Content-Type: application/json" \
  -d '{"prompt":"Create a forest"}'
```

With the default provider, the response is shaped as follows:

```json
{
  "response": {
    "content": "Mock response: Create a forest",
    "provider_name": "mock",
    "model": "mock-model",
    "finish_reason": "stop",
    "metadata": {
      "mode": "offline",
      "request_count": 1
    }
  }
}
```

Other available endpoints are `GET /providers` and `GET /providers/active`.

## Current limitations

- Only `MockProvider` is implemented; no external SDK integration exists.
- Providers are synchronous and in-memory; there is no streaming support.
- `ProviderCapabilities` exposes `structured_output` and `streaming` flags,
  but `MockProvider` leaves both disabled.
- There is no retry, timeout, failover, persistence, or automatic fallback.
- The active provider is selected at startup; the current API cannot switch it.
- `ProviderGenerationError` is defined and mapped by the API, but no bundled
  provider currently produces it.
- Unexpected exceptions from a future provider are not wrapped by
  `ProviderManager`; only a provider that raises `ProviderGenerationError`
  reaches the API's 502 mapping.
- Provider configuration is validated while the AppContainer is being built,
  before its Runtime worker is started. An unsupported `AI_PROVIDER` aborts
  container construction rather than leaving a running worker behind.
- The `placeholder` startup alias resolves to `MockProvider`/`mock`, rather
  than becoming an independently addressable provider name.
