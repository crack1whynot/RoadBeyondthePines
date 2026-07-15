# Unreal MCP Foundation

## Purpose

The Unreal MCP Foundation is a safe, asynchronous bridge boundary between
Road Beyond the Pines Studio and a future Unreal Editor Bridge. It gives the
backend one provider-neutral path for Unreal queries and explicitly prevents
the backend from importing the Unreal Python module, spawning processes, or
calling shell commands.

At v0.6.0 the default transport is an offline `MockUnrealTransport`. It works
without Unreal Engine, an Unreal project, an Editor plugin, or a network
connection. The optional HTTP transport is ready for a future bridge but does
not create a network client or connect during import or DI construction.

## Architecture

```text
UnrealService / legacy UnrealManager / API
                  |
                  v
          UnrealMCPManager
                  |
                  v
           UnrealMCPClient
                  |
                  v
          UnrealTransport (abstract)
             |                 |
             v                 v
 MockUnrealTransport   HTTPUnrealTransport
                                |
                                v
                    Future Unreal Editor Bridge
```

`backend.mcp` never imports `unreal`. An Unreal Editor plugin is intentionally
outside this milestone. The manager is the only high-level boundary exposed to
the application; agents and services do not access a transport or HTTP client
directly.

## Main modules

| Module | Responsibility |
| --- | --- |
| `backend/mcp/models.py` | Strict Pydantic request, result, health, connection, project, map, and asset models. |
| `backend/mcp/errors.py` | MCP error hierarchy and safe public `MCPErrorInfo` conversion. |
| `backend/mcp/commands.py` | Central catalog of allowed commands, descriptions, capabilities, and basic argument validation. |
| `backend/mcp/security.py` | Unknown-command denial, write policy, metadata secret checks, shell/subprocess denial, and controlled Python actions. |
| `backend/mcp/transport.py` | Abstract async `UnrealTransport` contract. |
| `backend/mcp/mock_transport.py` | Deterministic offline Unreal fixtures. |
| `backend/mcp/transports/http_transport.py` | Lazy stdlib HTTP transport for a future bridge. |
| `backend/mcp/registry.py` | Per-container transport-builder registry. |
| `backend/mcp/factory.py` | Fresh registry, transport, client, and manager construction from `Settings`. |
| `backend/mcp/client.py` | Connection lifecycle, timeouts, security enforcement, and transport-result normalization. |
| `backend/mcp/manager.py` | High-level lifecycle, command API, active client, and serialized write operations. |

## Unified models

The public command model is `MCPCommand`. It contains a generated string `id`,
non-empty `name`, independent `arguments` and `metadata` dictionaries,
optional positive `timeout_seconds`, `read_only`, and optional `request_id`.

`MCPCommandResult` returns the command id, success flag, optional data, safe
`MCPErrorInfo`, optional duration, and safe metadata. Public mapping values are
sanitized recursively: credential-looking keys and string values containing
credential markers (including Bearer values) are redacted, while stack,
trace, debug, and internal mapping fields are removed or redacted. This
sanitation also applies to bridge health and error messages.

Other models are `UnrealConnectionInfo`, `UnrealProjectInfo`,
`UnrealAssetInfo`, `UnrealMapInfo`, and `MCPHealthStatus`. API execution accepts
the narrower `MCPExecuteRequest` model: only `name` and `arguments` are
accepted from a public caller. Callers cannot provide `read_only`, timeout,
metadata, or a raw transport payload.

## Command lifecycle

```text
MCPExecuteRequest / manager wrapper
  -> UnrealMCPManager.execute(name, arguments)
  -> CommandCatalog + MCPSecurityPolicy
  -> UnrealMCPClient.execute(MCPCommand)
  -> UnrealTransport.execute(MCPCommand)
  -> MCPCommandResult
```

The manager gets the authoritative command definition from the catalog and
sets the command's `read_only` value itself. The client validates policy before
checking transport state, applies `asyncio.wait_for` timeout handling, then
normalizes failed transport results into MCP domain errors. Write commands that
are permitted by policy run under an async lock so writes are serialized.

## Transport abstraction

Every transport implements the async `UnrealTransport` contract:

- `connect() -> UnrealConnectionInfo`
- `disconnect() -> None`
- `is_connected() -> bool`
- `execute(command) -> MCPCommandResult`
- `health_check() -> MCPHealthStatus`
- `get_name()` and optional `get_capabilities()`

There is no global transport instance. `UnrealTransportRegistry` stores
builders, not live transports. A fresh registry is created for each DI
container and registers `mock` and `http`; duplicate builders require
`replace=True` explicitly. This makes future WebSocket support additive rather
than binding Studio to one Unreal plugin or protocol.

### Mock transport

`MockUnrealTransport` is the default. Its fixtures are stable and model a
RoadBeyondThePines Unreal 5.8 project with maps, assets, plugins, editor state,
and a fixed timestamp. It supports offline connect/disconnect/health and the
read-only catalog commands.

Examples of deterministic mock results:

- `unreal.ping` returns `{"message": "pong"}`.
- `unreal.get_project_info` returns RoadBeyondThePines project metadata.
- `unreal.list_maps` returns `L_PineRoad`, `L_ForestOutpost`, and `L_Prototype`.
- `unreal.list_assets` and `unreal.get_asset` return stable fixture assets.

It also simulates the non-dangerous writes `unreal.open_map`,
`unreal.save_current_level`, and `unreal.save_asset` once the security policy
allows them. Map and asset targets still have to be safe Unreal references. It
does not execute editor code, access the filesystem, use a subprocess, or
access a network.

### HTTP transport

`HTTPUnrealTransport` is optional and uses only Python's standard-library
`urllib` through `asyncio.to_thread`; no HTTP SDK dependency was added. It
creates its client lazily on the first bridge request. Tests inject a fake
sender or client, so they never make real HTTP calls. `disconnect()` closes an
already-created client and clears its connection state.

The transport maps timeouts to `MCPTimeoutError`, connection failures to
`MCPConnectionError`, malformed responses to `MCPProtocolError`, and HTTP
transport failures to `MCPTransportError`. Authorization is sent as a Bearer
header only when a non-empty auth token is configured. The token is neither
logged nor returned by API models. Redirects are rejected rather than followed,
so the header cannot be forwarded to a different bridge origin.

## Future Unreal Editor Bridge protocol

The HTTP transport expects a bridge below its configured base URL with these
endpoints:

### `GET /health`

Return a JSON object compatible with `MCPHealthStatus`, for example:

```json
{
  "healthy": true,
  "connected": true,
  "latency_ms": 1.2,
  "message": "Editor bridge is ready",
  "details": {}
}
```

### `GET /connection`

Return a JSON object compatible with `UnrealConnectionInfo`, for example:

```json
{
  "connected": true,
  "transport": "http",
  "engine_version": "5.8",
  "project_name": "RoadBeyondThePines",
  "project_path": "C:/Projects/RoadBeyondThePines",
  "editor_pid": 12345,
  "capabilities": ["project.read", "content.read"]
}
```

### `POST /commands`

Studio sends this body:

```json
{
  "id": "command-id",
  "name": "unreal.get_project_info",
  "arguments": {},
  "timeout_seconds": 10.0,
  "metadata": {},
  "read_only": true
}
```

The bridge must return a JSON object compatible with `MCPCommandResult`, such
as:

```json
{
  "command_id": "command-id",
  "success": true,
  "data": {
    "project_name": "RoadBeyondThePines"
  },
  "duration_ms": 3.5,
  "metadata": {}
}
```

The transport also accepts `connection`, `health`, or `result` wrapper objects
for their corresponding endpoints. A bridge must not put credentials, raw
stack traces, or internal transport diagnostics into public result fields.

## Command catalog and security

Read-only commands:

- `unreal.ping`
- `unreal.get_connection_info`
- `unreal.get_project_info`
- `unreal.get_editor_state`
- `unreal.list_maps`
- `unreal.get_current_map`
- `unreal.list_assets`
- `unreal.get_asset`
- `unreal.list_plugins`
- `unreal.run_python_readonly`

Write commands in the catalog:

- `unreal.open_map`
- `unreal.save_current_level`
- `unreal.save_asset`
- `unreal.run_python`
- `unreal.execute_editor_command`

Unknown commands are always rejected. `UNREAL_MCP_ALLOW_WRITE=false` is the
default, so every write command is rejected. When it is explicitly `true`, the
currently supported simulated write operations still require
`confirm_write=true` in their arguments. `unreal.run_python` and
`unreal.execute_editor_command` remain rejected in v0.6.0 even when writes are
enabled.

`unreal.run_python_readonly` does not receive a Python source string. It
accepts exactly one registered `action`: `get_selected_assets`,
`get_level_actors`, or `get_project_paths`.

Every catalog command has an argument allowlist; unsupported fields are denied
before they can reach a transport. Asset and map targets accept only virtual
`/Game/...` references (or a short Unreal map name for `unreal.open_map`), so
native Windows/Unix paths and traversal are denied. The policy also rejects
secret-bearing metadata, shell/PowerShell/cmd/bash/subprocess terms, and any
explicit filesystem path unless a future internally configured policy scopes it
to an allowed Unreal project path. No current catalog command accepts a
filesystem path.

## Configuration

All settings use the existing `backend.core.config.Settings` model and can be
provided through `.env`. `.env.example` contains safe defaults and no real
credential.

| Variable | Default | Meaning |
| --- | --- | --- |
| `UNREAL_MCP_TRANSPORT` | `mock` | Built-in transport builder: `mock` or `http`. |
| `UNREAL_MCP_HOST` | `127.0.0.1` | Safe localhost host used when base URL is empty. |
| `UNREAL_MCP_PORT` | `8765` | HTTP bridge port. |
| `UNREAL_MCP_BASE_URL` | empty | Optional absolute HTTP(S) bridge URL; overrides host/port. |
| `UNREAL_MCP_TIMEOUT_SECONDS` | `10` | Positive default timeout for connect, health, and commands. |
| `UNREAL_MCP_AUTO_CONNECT` | `false` | Connect during application lifespan start when enabled. |
| `UNREAL_MCP_ALLOW_WRITE` | `false` | Enables only policy-supported writes, still requiring confirmation. |
| `UNREAL_MCP_AUTH_TOKEN` | empty | Optional secret Bearer token for the HTTP bridge. |
| `UNREAL_MCP_ENABLED` | `false` | Retained legacy settings flag exposed by `/settings`; it is not a second transport control plane. |

`UNREAL_MCP_AUTH_TOKEN` is a `SecretStr` and is not returned from `/settings`,
`/unreal-mcp`, status models, error details, or logs. Keep its real value in a
private `.env` or deployment secret store; never put it in `.env.example` or
source control.

## DI and lifecycle integration

`create_app_container()` creates a fresh `UnrealTransportRegistry` and an
`UnrealMCPManager` from the active settings without connecting. It exposes the
manager in `AppContainer` and registers it in the existing Runtime Service
Registry as `"unreal_mcp_manager"`.

The FastAPI application creates the AppContainer during lifespan startup,
stores the manager in `app.state`, and uses this lifecycle order:

1. `runtime.start()` starts the local handler worker.
2. `await manager.start()` runs next and connects only when
   `UNREAL_MCP_AUTO_CONNECT=true`.
3. Connection errors during auto-connect are logged by code only and do not
   prevent backend startup.
4. `await manager.stop()` disconnects and closes any transport client during
   shutdown, before Runtime shutdown.

`UnrealService` is now a DI-managed adapter over the manager. The existing
`GET /management/unreal` endpoint retains `connected`, `status`, and `message`
fields and adds safe manager state. `backend/integrations/mcp.py` remains the
old synchronous `MCPClient` contract for compatibility; new code uses
`UnrealMCPClient`. The legacy `backend/agents/unreal_manager.py` accepts an
injected manager for explicit read helpers but keeps its autonomous `run()`
entry point unsupported. The canonical Agent System's `UnrealAgent` receives
an opaque manager port through DI but intentionally returns
`FAILED/NOT_IMPLEMENTED`; it does not call an MCP transport in Phase 0.

## HTTP API

| Endpoint | Behavior |
| --- | --- |
| `GET /unreal-mcp/status` | Safe connected/health/transport/engine/project/capabilities/write state. |
| `GET /unreal-mcp/commands` | Catalog entries with read-only/write status and policy availability. |
| `POST /unreal-mcp/connect` | Explicitly connects the selected transport. Mock works offline. |
| `POST /unreal-mcp/disconnect` | Disconnects and releases transport resources. |
| `POST /unreal-mcp/execute` | Executes a catalogued command from `{ "name", "arguments" }`. |

Domain errors map to safe HTTP responses: 400 for invalid input, 404 for an
unknown command, 403 for rejected or disallowed commands, 503 for unavailable
or disconnected transports, 504 for timeouts, and 502 for transport, protocol,
or Unreal-side errors. Validation feedback contains only field locations and
error types, never rejected input values. Raw exception text and auth tokens
are not returned.

### Python example

```python
import asyncio

from backend.core.config import Settings
from backend.mcp.factory import create_unreal_mcp_manager


async def main() -> None:
    manager = create_unreal_mcp_manager(Settings(unreal_mcp_transport="mock"))
    await manager.connect()
    result = await manager.get_project_info()
    print(result.data["project_name"])
    await manager.stop()


asyncio.run(main())
```

### HTTP example

Connect the default mock transport, then execute a read-only command:

```bash
curl -X POST "http://127.0.0.1:8000/unreal-mcp/connect"

curl -X POST "http://127.0.0.1:8000/unreal-mcp/execute" \
  -H "Content-Type: application/json" \
  -d '{"name":"unreal.get_project_info","arguments":{}}'
```

## Current limitations and intentionally excluded work

- No Unreal Editor plugin or concrete Editor Bridge is included.
- No Blueprint graph generation, full gameplay-system generation, C++ changes,
  C++ compilation, packaging, or packaged-build execution is implemented.
- No Git operations, Command Center UI, Project Manager, or autonomous Editor
  control is implemented.
- Mock data is deterministic and useful for tests, but does not reflect a live
  Unreal project.
- HTTP support covers only the documented future bridge protocol and is not
  tested against a live Unreal Editor.
- There is no WebSocket transport yet; the builder registry is the extension
  point for it.
- There are no retries, durable command history, or remote write automation.
- Dangerous arbitrary Python and editor-command execution remain unavailable.
