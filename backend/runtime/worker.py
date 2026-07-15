"""Worker that executes registered runtime handlers and records real results."""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from typing import Any, Protocol

from backend.core.execution import ExecutionStatus
from backend.core.logging import get_logger
from backend.runtime.task_queue import Job, JobResult, TaskQueue

logger = get_logger("runtime.worker")

JobHandlerResolver = Callable[[str], Any | None]


class WorkerProtocol(Protocol):
    def start(self) -> None:
        ...

    def stop(self, *, drain: bool = False, timeout: float | None = 5.0) -> None:
        ...

    def attach_task_queue(self, queue: TaskQueue) -> None:
        ...

    def attach_handler_resolver(self, resolver: JobHandlerResolver) -> None:
        ...


class Worker:
    """Single-threaded job worker with cooperative cancellation and timeouts.

    A timed out synchronous handler cannot be forcefully stopped safely in
    Python.  The worker records ``TIMED_OUT`` (or ``CANCELLED``) immediately
    and lets that daemon handler thread finish in the background.  Handlers
    that perform long work should therefore check ``job.cancelled``.
    """

    def __init__(self, *, poll_interval: float = 0.05) -> None:
        self._queue: TaskQueue | None = None
        self._handler_resolver: JobHandlerResolver | None = None
        self._poll_interval = poll_interval
        self._running = False
        self._stop_requested = False
        self._drain_on_stop = False
        self._thread: threading.Thread | None = None
        self._lock = threading.RLock()

    @property
    def running(self) -> bool:
        with self._lock:
            return self._running

    def attach_task_queue(self, queue: TaskQueue) -> None:
        self._queue = queue

    def attach_handler_resolver(self, resolver: JobHandlerResolver) -> None:
        self._handler_resolver = resolver

    def start(self) -> None:
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                if self._stop_requested:
                    raise RuntimeError("Worker is still stopping and cannot be restarted yet")
                return
            self._stop_requested = False
            self._drain_on_stop = False
            self._running = True
            self._thread = threading.Thread(
                target=self._run_loop,
                name="runtime-worker",
                daemon=True,
            )
            self._thread.start()
        logger.info("Worker started")

    def stop(self, *, drain: bool = False, timeout: float | None = 5.0) -> None:
        """Stop the worker and join its thread.

        ``drain=True`` processes already queued work before stopping.  It is
        used by runtime shutdown so accepted jobs are not silently discarded.
        """

        with self._lock:
            thread = self._thread
            if thread is None:
                self._running = False
                return
            self._stop_requested = True
            self._drain_on_stop = drain

        # ``dequeue`` waits on the queue condition; a zero-timeout dequeue is
        # unnecessary because the normal polling bound is small.
        if thread is not threading.current_thread():
            thread.join(timeout)

        if thread.is_alive():
            logger.warning("Worker did not stop within the configured timeout")
            return

        with self._lock:
            if self._thread is thread:
                self._thread = None
                self._running = False
        logger.info("Worker stopped")

    def _should_stop(self) -> bool:
        with self._lock:
            stop_requested = self._stop_requested
            drain_on_stop = self._drain_on_stop
        if not stop_requested:
            return False
        if not drain_on_stop:
            return True
        return self._queue is None or not self._queue.has_queued_jobs()

    def _run_loop(self) -> None:
        try:
            while not self._should_stop():
                queue = self._queue
                if queue is None:
                    time.sleep(self._poll_interval)
                    continue

                job = queue.dequeue(timeout=self._poll_interval)
                if job is None:
                    continue
                if not queue.mark_running(job.id):
                    continue

                logger.info("Processing job %s with handler %s", job.id, job.effective_handler_name)
                queue.complete(job.id, self._execute_job(job))
        finally:
            with self._lock:
                self._running = False

    def _execute_job(self, job: Job) -> JobResult:
        handler = self._resolve_handler(job.effective_handler_name)
        if handler is None:
            return JobResult(
                success=False,
                status=ExecutionStatus.FAILED,
                error=f"No handler is registered for '{job.effective_handler_name}'",
                error_code="HANDLER_NOT_FOUND",
            )

        state: dict[str, Any] = {}
        completed = threading.Event()

        def invoke() -> None:
            try:
                state["result"] = self._invoke_handler(handler, job)
            except Exception:  # noqa: BLE001 - boundary converts arbitrary handlers safely
                logger.exception("Job %s handler %s failed", job.id, job.effective_handler_name)
                state["exception"] = True
            finally:
                completed.set()

        handler_thread = threading.Thread(
            target=invoke,
            name=f"runtime-job-{job.id}",
            daemon=True,
        )
        handler_thread.start()
        started = time.monotonic()

        while not completed.wait(self._poll_interval):
            if job.cancelled:
                return JobResult(
                    success=False,
                    status=ExecutionStatus.CANCELLED,
                    error="Job was cancelled during execution",
                    error_code="JOB_CANCELLED",
                )
            if job.timeout_seconds is not None and time.monotonic() - started >= job.timeout_seconds:
                return JobResult(
                    success=False,
                    status=ExecutionStatus.TIMED_OUT,
                    error="Job exceeded its execution timeout",
                    error_code="JOB_TIMEOUT",
                )

        if job.cancelled:
            return JobResult(
                success=False,
                status=ExecutionStatus.CANCELLED,
                error="Job was cancelled during execution",
                error_code="JOB_CANCELLED",
            )
        if state.get("exception"):
            return JobResult(
                success=False,
                status=ExecutionStatus.FAILED,
                error="Job handler raised an exception",
                error_code="HANDLER_EXCEPTION",
            )
        return self._normalise_result(state.get("result"))

    def _resolve_handler(self, handler_name: str) -> Any | None:
        if self._handler_resolver is None:
            return None
        try:
            return self._handler_resolver(handler_name)
        except Exception:  # noqa: BLE001 - a bad registry must not kill the worker
            logger.exception("Could not resolve runtime handler %s", handler_name)
            return None

    @staticmethod
    def _invoke_handler(handler: Any, job: Job) -> Any:
        if hasattr(handler, "handle"):
            return handler.handle(job)
        if callable(handler):
            return handler(job)
        raise TypeError("Registered job handler is neither callable nor has a handle() method")

    @staticmethod
    def _normalise_result(raw_result: Any) -> JobResult:
        """Adapt simple handler returns and canonical AgentResult-like values."""

        if isinstance(raw_result, JobResult):
            return raw_result

        if raw_result is None:
            return JobResult(
                success=False,
                status=ExecutionStatus.FAILED,
                error="Job handler returned no result",
                error_code="INVALID_HANDLER_RESULT",
            )

        if isinstance(raw_result, dict):
            has_success = "success" in raw_result
            success = bool(raw_result["success"]) if has_success else False
            status_value = raw_result.get("status")
            payload = raw_result.get("output", raw_result.get("payload", raw_result))
            error = raw_result.get("error")
            error_code = raw_result.get("error_code")
            metadata = raw_result.get("metadata", {})
        else:
            success_value = getattr(raw_result, "success", None)
            has_success = success_value is not None
            success = bool(success_value) if has_success else True
            status_value = getattr(raw_result, "status", None)
            # Preserve structured higher-level results (notably AgentResult)
            # so the Orchestrator can aggregate truthful task identity,
            # status, timing, and metadata.  JobResult.output unwraps its
            # user-facing output for callers that only need the payload.
            payload = raw_result
            error = getattr(raw_result, "error", None)
            error_code = getattr(raw_result, "error_code", None)
            metadata = getattr(raw_result, "metadata", {})

        status: ExecutionStatus | None = None
        if status_value is not None:
            candidate = getattr(status_value, "value", status_value)
            try:
                status = ExecutionStatus(candidate)
            except (TypeError, ValueError):
                # A lifecycle enum (for example AgentStatus.IDLE) must not be
                # mistaken for successful execution state.
                status = None

        if isinstance(raw_result, dict) and not has_success and status is None:
            return JobResult(
                success=False,
                status=ExecutionStatus.FAILED,
                error="Job handler returned a dictionary without an execution result",
                error_code="INVALID_HANDLER_RESULT",
            )
        if not isinstance(raw_result, dict) and status_value is not None and status is None and not has_success:
            return JobResult(
                success=False,
                status=ExecutionStatus.FAILED,
                error="Job handler returned a non-execution status without success",
                error_code="INVALID_HANDLER_RESULT",
            )

        if status is None:
            status = ExecutionStatus.SUCCEEDED if success else ExecutionStatus.FAILED
        if not status.is_terminal:
            return JobResult(
                success=False,
                status=ExecutionStatus.FAILED,
                error="Job handler returned a non-terminal execution status",
                error_code="INVALID_HANDLER_RESULT",
            )

        if not status is ExecutionStatus.SUCCEEDED and error is None:
            error = "Job handler reported an unsuccessful result"
            error_code = error_code or "HANDLER_REPORTED_FAILURE"

        return JobResult(
            success=success,
            payload=payload,
            error=error,
            status=status,
            error_code=error_code,
            metadata=metadata if isinstance(metadata, dict) else {},
        )
