# Legacy Agent Migration

## Status

`backend/agent_system` is canonical. `backend/agents` is legacy and must not
be used for new work.

The packages have incompatible contracts:

| Legacy package | Canonical package |
| --- | --- |
| `BaseAgent.run()` | `BaseAgent.execute(task, context) -> AgentResult` |
| No execution outcome contract | `ExecutionStatus` plus a structured AgentResult |
| Not registered by DI | One `AgentRegistry`, `AgentFactory`, `AgentLoader`, and `AgentManager` |
| No Runtime dispatch integration | Runtime `agent.dispatch` handler |

Static Phase 0 audit found no route or test that instantiates a legacy agent.
The compatibility package remains so old imports do not immediately break, but
DI, Runtime, Planner, and new APIs do not create legacy agents.

## Existing exception

`backend.agents.unreal_manager.UnrealManager` can be manually constructed with
an `UnrealMCPManager` and exposes async read helpers for project information
and maps. Its legacy `run()` method remains unsupported. It is not the
canonical `UnrealAgent`, is not wired into DI, and must not be used to bypass
the MCP manager or Runtime.

## Migration steps

1. Replace imports from `backend.agents` with the appropriate
   `backend.agent_system` types.
2. Model input as `AgentTask` and `AgentContext` rather than a parameterless
   `run()` call.
3. Return `AgentResult.succeeded(...)` only after a real operation, or
   `AgentResult.failed(..., code="NOT_IMPLEMENTED")` until one exists.
4. Register the implementation through `AgentFactory`/`AgentLoader`, not by
   reflection or a second registry.
5. Let Orchestrator queue it through Runtime instead of calling it from a
   route.

Legacy files may be removed only after all external consumers have migrated
and a compatibility-release policy has been agreed. Do not add new legacy
agents or a second legacy registry/manager.
