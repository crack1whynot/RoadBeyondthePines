# Runtime Layer

## Purpose

`backend.runtime` is the in-process execution boundary for Phase 0. It owns a
single priority queue, a single worker thread, a registered handler map, and
in-process job/result records. Constructing `Runtime` has no worker side effect;
`start()` is called by FastAPI lifespan. `initialize()` and `shutdown()` remain
compatibility aliases for `start()` and `stop()`.

## Execution contract

```text
Runtime.enqueue_job(Job)
  -> TaskQueue records QUEUED job
  -> Worker dequeues it and marks RUNNING
  -> Worker resolves Job.handler_name (or Job.name)
  -> handler executes
  -> TaskQueue stores the terminal JobResult
```

Available terminal and in-flight execution states are:

```text
PENDING, QUEUED, RUNNING, SUCCEEDED, FAILED, CANCELLED, TIMED_OUT
```

`SUCCEEDED` is set only after the handler returns a valid successful terminal
result. The worker records `FAILED/HANDLER_NOT_FOUND` when no handler exists,
`FAILED/HANDLER_EXCEPTION` for an exception, and `FAILED/INVALID_HANDLER_RESULT`
when a handler returns no usable execution result. It does not manufacture a
completed result merely because it dequeued work.

Public Runtime APIs are `register_handler`, `unregister_handler`,
`has_handler`, `enqueue_job`, `get_job`, `get_job_result`, `wait_for_job`, and
`cancel_job`.

## Lifecycle

- `start()` registers core services once, opens the queue, attaches the worker
  to the handler resolver, and starts the worker.
- `stop()` stops accepting new Runtime jobs, drains queued jobs where possible,
  joins the worker, unloads plugins, and closes the queue.
- A stopped Runtime may be started again; queue initialization reopens the
  queue for new jobs.
- Queue enqueue after shutdown raises a clear `RuntimeError`.

Python cannot safely force-stop a synchronous handler thread. For a timeout
or cancellation, Runtime records `TIMED_OUT` or `CANCELLED` immediately and
the handler is expected to cooperate by checking its Job state. This is an
intentional Phase 0 limitation, not a claim of hard cancellation.

## Services and plugins

`ServiceRegistry` rejects accidental duplicate names unless `replace=True` is
explicit. `PluginLoader.reload_plugin()` retains the loaded plugin instance,
unloads it, then loads it again; it no longer deletes the instance before a
reload attempt.

The queue/result store is process-local and non-durable. It is suitable for the
diagnostic pipeline and tests, not crash recovery or distributed execution.
