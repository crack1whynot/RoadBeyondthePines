"""Durable in-process job queue used by the Phase 0 execution pipeline."""

from __future__ import annotations

import heapq
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Protocol
from uuid import uuid4

from backend.core.execution import ExecutionStatus
from backend.core.logging import get_logger

logger = get_logger("runtime.task_queue")

# Keep the historical import path working while making execution state shared
# with the Agent System and Orchestrator.
JobStatus = ExecutionStatus


class JobPriority(int, Enum):
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class JobContext:
    correlation_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class JobResult:
    """Actual result produced by a job handler.

    ``success`` is derived from the final execution status so callers cannot
    accidentally report a successful cancelled, timed-out, or failed job.
    """

    success: bool
    payload: Any = None
    error: str | None = None
    status: ExecutionStatus | None = None
    error_code: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    duration_ms: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.status is None:
            self.status = ExecutionStatus.SUCCEEDED if self.success else ExecutionStatus.FAILED
        elif not isinstance(self.status, ExecutionStatus):
            self.status = ExecutionStatus(self.status)

        if not self.status.is_terminal:
            raise ValueError("JobResult status must be terminal")
        self.success = self.status is ExecutionStatus.SUCCEEDED

    @property
    def output(self) -> Any:
        """Return the user-facing output, unwrapping structured payloads."""

        return getattr(self.payload, "output", self.payload)


@dataclass
class Job:
    """A unit of work processed by the runtime worker."""

    # ``id, name`` preserves the original positional construction order while
    # still giving new callers a collision-resistant default identifier.
    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    payload: dict[str, Any] = field(default_factory=dict)
    handler_name: str | None = None
    priority: JobPriority = JobPriority.NORMAL
    status: ExecutionStatus = ExecutionStatus.PENDING
    retries: int = 0
    max_retries: int = 3
    context: JobContext = field(default_factory=JobContext)
    progress: float = 0.0
    timeout_seconds: float | None = None
    cancelled: bool = False
    result: JobResult | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    _completion_event: threading.Event = field(default_factory=threading.Event, repr=False)

    @property
    def effective_handler_name(self) -> str:
        """Use the job name as the backward-compatible handler key."""

        return self.handler_name or self.name


class TaskQueueProtocol(Protocol):
    def initialize(self) -> None:
        ...

    def enqueue(self, job: Job) -> None:
        ...

    def dequeue(self, timeout: float | None = 0) -> Job | None:
        ...

    def cancel(self, job_id: str) -> bool:
        ...

    def shutdown(self, *, cancel_pending: bool = True) -> None:
        ...


class TaskQueue:
    """Thread-safe priority queue with durable job and result records."""

    def __init__(self) -> None:
        self._heap: list[tuple[int, int, str]] = []
        self._jobs: dict[str, Job] = {}
        self._results: dict[str, JobResult] = {}
        self._lock = threading.RLock()
        self._condition = threading.Condition(self._lock)
        self._shutdown = False
        self._sequence = 0

    @property
    def is_shutdown(self) -> bool:
        with self._lock:
            return self._shutdown

    def initialize(self) -> None:
        """Open the queue for a (possibly restarted) runtime."""

        with self._condition:
            self._shutdown = False
            self._condition.notify_all()
        logger.debug("Task queue initialized")

    def enqueue(self, job: Job) -> None:
        """Store and queue a new job.

        Reusing a job identifier would make result lookup ambiguous, so it is
        rejected rather than silently replacing historical state.
        """

        with self._condition:
            if self._shutdown:
                raise RuntimeError("Task queue is shut down and cannot accept new jobs")
            if job.id in self._jobs:
                raise ValueError(f"Job '{job.id}' is already known to the task queue")

            job.status = ExecutionStatus.QUEUED
            job.cancelled = False
            job.result = None
            job.started_at = None
            job.finished_at = None
            job.progress = 0.0
            job._completion_event.clear()
            self._jobs[job.id] = job
            self._sequence += 1
            heapq.heappush(self._heap, (-int(job.priority), self._sequence, job.id))
            self._condition.notify()
        logger.debug("Enqueued job %s with handler %s", job.id, job.effective_handler_name)

    def dequeue(self, timeout: float | None = 0) -> Job | None:
        """Return the next executable job, waiting up to ``timeout`` seconds."""

        with self._condition:
            if timeout is not None and timeout < 0:
                raise ValueError("timeout must be non-negative or None")

            deadline = None if timeout is None else time.monotonic() + timeout
            while True:
                while self._heap:
                    _, _, job_id = heapq.heappop(self._heap)
                    job = self._jobs.get(job_id)
                    if job is None or job.status is not ExecutionStatus.QUEUED:
                        continue
                    return job

                if self._shutdown:
                    return None
                if timeout == 0:
                    return None

                remaining = None if deadline is None else deadline - time.monotonic()
                if remaining is not None and remaining <= 0:
                    return None
                self._condition.wait(remaining)

    def mark_running(self, job_id: str) -> bool:
        """Transition a queued job to running, unless it was cancelled."""

        with self._condition:
            job = self._jobs.get(job_id)
            if job is None or job.status is not ExecutionStatus.QUEUED:
                return False
            if job.cancelled:
                self._finish_locked(
                    job,
                    JobResult(
                        success=False,
                        status=ExecutionStatus.CANCELLED,
                        error="Job was cancelled before execution",
                        error_code="JOB_CANCELLED",
                    ),
                )
                return False

            job.status = ExecutionStatus.RUNNING
            job.started_at = _utcnow()
            self._condition.notify_all()
            return True

    def complete(self, job_id: str, result: JobResult) -> JobResult | None:
        """Persist an actual terminal result for a running job."""

        with self._condition:
            job = self._jobs.get(job_id)
            if job is None:
                return None
            if job.status.is_terminal:
                return job.result

            if job.cancelled and result.status is not ExecutionStatus.CANCELLED:
                result = JobResult(
                    success=False,
                    status=ExecutionStatus.CANCELLED,
                    error="Job was cancelled during execution",
                    error_code="JOB_CANCELLED",
                    metadata=result.metadata,
                )
            self._finish_locked(job, result)
            return job.result

    def _finish_locked(self, job: Job, result: JobResult) -> None:
        if job.status.is_terminal:
            return

        finished_at = _utcnow()
        result.started_at = result.started_at or job.started_at or finished_at
        result.finished_at = result.finished_at or finished_at
        if result.duration_ms is None:
            result.duration_ms = max(
                0.0,
                (result.finished_at - result.started_at).total_seconds() * 1000,
            )

        job.status = result.status
        job.result = result
        job.finished_at = result.finished_at
        job.progress = 1.0 if result.success else job.progress
        self._results[job.id] = result
        job._completion_event.set()
        self._condition.notify_all()

    def cancel(self, job_id: str) -> bool:
        """Request cancellation and finish jobs that have not started yet."""

        with self._condition:
            job = self._jobs.get(job_id)
            if job is None or job.status.is_terminal:
                return False

            job.cancelled = True
            if job.status in {ExecutionStatus.PENDING, ExecutionStatus.QUEUED}:
                self._finish_locked(
                    job,
                    JobResult(
                        success=False,
                        status=ExecutionStatus.CANCELLED,
                        error="Job was cancelled before execution",
                        error_code="JOB_CANCELLED",
                    ),
                )
            self._condition.notify_all()
            return True

    def get_job(self, job_id: str) -> Job | None:
        with self._lock:
            return self._jobs.get(job_id)

    def get_job_result(self, job_id: str) -> JobResult | None:
        with self._lock:
            return self._results.get(job_id)

    def wait_for_job(self, job_id: str, timeout: float | None = None) -> JobResult | None:
        """Wait for a job's terminal result; return ``None`` on wait timeout."""

        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return None
            completion_event = job._completion_event
        if not completion_event.wait(timeout):
            return None
        return self.get_job_result(job_id)

    def has_queued_jobs(self) -> bool:
        with self._lock:
            return any(job.status is ExecutionStatus.QUEUED for job in self._jobs.values())

    def shutdown(self, *, cancel_pending: bool = True) -> None:
        """Stop accepting work and optionally cancel unfinished jobs."""

        with self._condition:
            self._shutdown = True
            if cancel_pending:
                for job in self._jobs.values():
                    if job.status in {
                        ExecutionStatus.PENDING,
                        ExecutionStatus.QUEUED,
                        ExecutionStatus.RUNNING,
                    }:
                        job.cancelled = True
                        self._finish_locked(
                            job,
                            JobResult(
                                success=False,
                                status=ExecutionStatus.CANCELLED,
                                error="Runtime shut down before job completion",
                                error_code="RUNTIME_SHUTDOWN",
                            ),
                        )
                self._heap.clear()
            self._condition.notify_all()
        logger.debug("Task queue shutdown")
