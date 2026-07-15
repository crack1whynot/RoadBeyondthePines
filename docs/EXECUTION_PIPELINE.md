# Phase 0 Execution Pipeline

## Scope

Phase 0 proves one truthful local execution path. It does not implement game
generation, a real AI provider, a live Unreal Editor bridge, Git automation,
or autonomous development.

## Sequence

```text
POST /brain/execute {"request_text":"diagnostic: pine-road"}
  -> DevelopmentRequestService creates request_id
  -> Brain.analyze creates a unique Goal
  -> Orchestrator.execute_goal creates an ExecutionPlan
  -> Planner creates a unique diagnostic.execute task
  -> Orchestrator checks AgentManager capabilities
  -> Scheduler queues a Job(handler_name="agent.dispatch")
  -> Runtime Worker resolves and runs that handler
  -> AgentManager selects DiagnosticAgent and calls execute()
  -> AgentResult is persisted in the Runtime JobResult
  -> ResultCollector aggregates actual AgentResults
  -> DevelopmentRequestService persists a sanitised memory summary
  -> API returns the actual plan/task outcome
```

The Runtime wraps the AgentManager invocation so queue state, timeout,
cancellation, and durable in-process job result handling are all observable.
The Orchestrator also calls AgentManager for capability preflight; it never
marks a task successful itself.

## Responsibilities

| Component | Does | Does not do |
| --- | --- | --- |
| Brain | Builds context and a Goal | Start workers or directly execute tasks |
| Orchestrator | Plans, checks dependencies/capabilities, queues tasks, aggregates outcomes | Invent task success |
| AgentManager | Selects an eligible agent and manages lifecycle around `execute()` | Own the queue/worker |
| Runtime | Executes registered handlers and persists JobResult | Choose an agent or plan work |
| ResultCollector | Counts/serialises supplied AgentResults | Create results for unscheduled work |
| Memory | Stores a best-effort sanitised summary | Change execution outcome after the fact |

## Statuses

Task and Job statuses are `PENDING`, `QUEUED`, `RUNNING`, `SUCCEEDED`,
`FAILED`, `CANCELLED`, and `TIMED_OUT`. Agent lifecycle is separate (`IDLE`,
`BUSY`, `OFFLINE`, `ERROR`, and administrative states). A successful task is
only `SUCCEEDED`; lifecycle `IDLE` is never task success.

Plan statuses are `PENDING`, `RUNNING`, `SUCCEEDED`, `PARTIALLY_SUCCEEDED`,
`FAILED`, and `CANCELLED`.

## Failures and dependencies

- Missing Runtime handler: `FAILED/HANDLER_NOT_FOUND`.
- Handler exception: `FAILED/HANDLER_EXCEPTION`, without a public traceback.
- Runtime timeout/cancellation: `TIMED_OUT` or `CANCELLED`.
- No enabled capable agent: `FAILED/NO_CAPABLE_AGENT`.
- Unimplemented built-in agent: `FAILED/NOT_IMPLEMENTED`.
- A required failed, cancelled, or timed-out dependency: dependent task is
  `CANCELLED/DEPENDENCY_FAILED` and is not dispatched.
- Unknown or unsupported request: HTTP 422 with the safe Phase 0 message.

## Memory persistence

After execution, the application service records request ID, timestamp, Goal
summary, plan ID/status, and task result summaries. Secret-shaped mapping keys
and common `api_key`, token, password, authorization, and secret values are
redacted; full stack traces are never written. If storage writes fail, the API
returns the real execution result with `MEMORY_PERSISTENCE_FAILED` in
`warnings` and `memory_persisted: false` metadata.

## Example

```bash
curl -X POST http://127.0.0.1:8000/brain/execute \
  -H "Content-Type: application/json" \
  -d '{"request_text":"diagnostic: pine-road"}'
```

The result contains a successful DiagnosticAgent task whose `output` is
`"pine-road"`. The same request through `/orchestrator/request?request_text=...`
executes without the Brain/Memory application-service wrapper.

## Current limitations

- Only one local diagnostic/echo task is supported.
- Execution is synchronous inside a single worker process; independent tasks
  are deliberately executed sequentially in this milestone.
- Cancellation and timeout are cooperative for blocking synchronous handlers.
- Job/results and AgentRegistry are in-memory and not crash-durable.
- Memory JSON persistence has no transaction, lock, or recovery guarantee.
- Provider and MCP managers are DI ports only in this path; no remote AI model
  or Unreal command is invoked.
