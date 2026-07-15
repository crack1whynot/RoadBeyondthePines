# Brain Layer

`Brain` is responsible for analysis and Goal creation, not worker control. Its
public `analyze(request_text)` method builds a `BrainContext`, asks the rule
based `DecisionEngine` for a decision, creates a UUID-backed `Goal`, and stores
that Goal in its in-memory `GoalManager`.

For an explicit `diagnostic` or `echo` request, the decision target is
`diagnostic.execute`. Other requests currently receive a broad project,
backend, or frontend analysis target; that is not a promise that they are
executable.

## Actual handoff

`POST /brain/analyze` remains analysis-only. `POST /brain/execute` uses
`DevelopmentRequestService`:

```text
request -> Brain.analyze -> Goal -> Orchestrator.execute_goal
        -> Runtime-backed agent dispatch -> actual result
```

The service reads the original request from Goal metadata, so it does not rely
on a fixed Goal ID or parse a display description. After execution it stores a
sanitised, best-effort summary in `ProjectMemory`; a memory failure becomes a
warning and does not turn an already-completed execution into failure.

## Current limits

`ContextBuilder` receives settings through DI and builds a local project
snapshot. It does not yet crawl project files, retrieve Memory entries, call a
provider, or inspect Git/Unreal state. The Planner has an optional Provider
Manager port but Phase 0 deliberately does not call it. Only explicit
diagnostic/echo requests are executable; other requests are rejected by the
Planner with an unsupported-request domain error.
