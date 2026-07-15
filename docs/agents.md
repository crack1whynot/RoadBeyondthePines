# Agent System

## Canonical layer

`backend/agent_system` is the only agent layer used by the Phase 0 execution
pipeline. It uses `AgentTask`, `AgentContext`, `AgentResult`, `AgentRegistry`,
`AgentFactory`, `AgentLoader`, and `AgentManager`.

`backend/agents` is legacy. It has the older abstract `run()` contract and is
not instantiated, registered, or dispatched by the Runtime. See
`LEGACY_AGENT_MIGRATION.md` before changing a legacy import.

## Task outcome versus agent lifecycle

Agent lifecycle is separate from task outcome:

- Lifecycle uses `AgentStatus`, including `IDLE`, `BUSY`, `OFFLINE`, and
  `ERROR` (with a few administrative states).
- Task outcome uses shared `ExecutionStatus`: `PENDING`, `QUEUED`, `RUNNING`,
  `SUCCEEDED`, `FAILED`, `CANCELLED`, or `TIMED_OUT`.

`AgentResult.success` is derived and is `True` only for `SUCCEEDED`. It
contains a task ID, agent ID, status, output, safe error, start/finish times,
duration, and metadata. Stack traces are logged internally rather than exposed
through this public result.

## Dispatch

The Runtime invokes the registered `agent.dispatch` handler. That handler calls
`AgentManager.dispatch_task()`:

1. It selects an enabled `IDLE` agent that supports **all** required
   capabilities.
2. Selection is deterministic: higher configured priority first, then name.
3. The selected agent moves to `BUSY`, executes synchronously, and normally
   returns to `IDLE`.
4. A missing capable agent returns `FAILED/NO_CAPABLE_AGENT`; an exception
   returns `FAILED/AGENT_EXECUTION_FAILED` and leaves the agent in `ERROR`.

`AgentLoader` has a fixed deterministic built-in list and creates all agents
through `AgentFactory`; reflection-based discovery is not used.

## Built-ins in this milestone

`DiagnosticAgent` is the only real execution agent. It supports
`diagnostic.execute` and `system.echo`, and returns the supplied task payload
unchanged.

World, Gameplay, Vehicle, UI, Animation, Audio, Networking, Testing,
Documentation, Git, Unreal, and Project Manager agents are present as explicit
failure boundaries. They return `FAILED` with `NOT_IMPLEMENTED`; they do not
claim that work occurred. `UnrealAgent` receives an optional opaque MCP manager
port from DI, but it does not call a transport or perform Unreal work yet.
