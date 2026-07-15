# Architecture Overview

## Current Phase 0 boundary

Road Beyond the Pines Studio now has one honest, in-process execution path for
an explicitly requested diagnostic operation. It is a foundation for future
studio automation, not an implementation of autonomous Unreal development.

```text
POST /brain/execute
  -> DevelopmentRequestService
  -> Brain.analyze()
  -> Orchestrator / Planner
  -> Runtime queue + Worker
  -> registered agent.dispatch handler
  -> AgentManager -> DiagnosticAgent
  -> actual AgentResult -> ResultCollector
  -> best-effort ProjectMemory summary
```

The Runtime is the execution boundary: a task is successful only after a
registered handler returns a successful terminal result. A missing handler,
handler exception, cancellation, timeout, invalid handler result, unavailable
agent, or failed dependency cannot be represented as success.

## Layers and ownership

| Layer | Current responsibility |
| --- | --- |
| FastAPI | HTTP validation, safe domain-error mapping, lifespan, and health reporting. |
| `AppContainer` | The single composition root. It owns one Runtime, AgentRegistry, AgentManager, Orchestrator, Brain, Memory, ProviderManager, and UnrealMCPManager for an application lifespan. |
| Brain | Builds a context and a unique Goal. `analyze()` remains analysis-only. |
| `DevelopmentRequestService` | Application use case that hands a Brain Goal to the Orchestrator and persists a sanitised summary. |
| Orchestrator | Creates a dependency-aware plan, performs capability preflight, queues ready tasks, and aggregates only actual results. |
| Agent System | The canonical agent layer: selection, lifecycle, and local execution contract. |
| Runtime | Registered handler lookup, queue, worker lifecycle, cancellation, timeout observation, and durable in-process job results. |
| Memory | In-memory structured records with optional JSON persistence; execution persistence is best effort. |
| Providers / Unreal MCP | Optional DI ports. They are not invoked by the Phase 0 diagnostic execution path. |

`backend/agents` is a legacy package with the incompatible `run()` contract.
It is not created by DI and is not on the execution path. New agent work belongs
in `backend/agent_system`.

## Lifecycle and DI

Importing `backend.app.main.app` creates no `AppContainer` and starts no
worker. During FastAPI lifespan startup, the app creates a container, loads
built-in canonical agents, registers the `agent.dispatch` Runtime handler,
starts Runtime, then starts Unreal MCP. Shutdown stops MCP before stopping the
Runtime.

The Runtime Service Registry is retained only for compatibility lookups such
as `orchestrator`, `ai_provider_manager`, and `unreal_mcp_manager`. The
container is the source of dependency wiring. Duplicate service registration
requires `replace=True` and otherwise raises an error.

## Supported execution scope

The rule-based Planner accepts only an explicit `diagnostic` or `echo` request
such as `diagnostic: verify pipeline`. It creates one UUID-backed task with
the `diagnostic.execute` capability. `DiagnosticAgent` returns the supplied
payload unchanged as a real local operation. Other built-in agents return a
terminal `FAILED` result with `NOT_IMPLEMENTED`.

Unknown product, Unreal, Blueprint, build, Git, or AI-generation requests are
rejected as unsupported rather than decomposed into fake work.

## Deliberate next steps

- Add real, bounded agent implementations before enabling their capabilities.
- Add production persistence, authorization, audit, and rate controls before
  enabling remote or write-capable automation.
- Add concrete AI-provider and Unreal Editor bridge implementations through
  their existing ports.
- Add durable task history, retries, and distributed execution only as a
  separate design phase.
