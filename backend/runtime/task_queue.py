from __future__ import annotations

import heapq
import threading
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Protocol

from backend.core.logging import get_logger

logger = get_logger("runtime.task_queue")


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobPriority(int, Enum):
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


@dataclass
class JobContext:
    correlation_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class JobResult:
    success: bool
    payload: Any = None
    error: str | None = None


@dataclass
class Job:
    """Unit of work processed by the queue."""

    id: str
    name: str
    payload: dict[str, Any] = field(default_factory=dict)
    priority: JobPriority = JobPriority.NORMAL
    status: JobStatus = JobStatus.PENDING
    retries: int = 0
    max_retries: int = 3
    context: JobContext = field(default_factory=JobContext)
    progress: float = 0.0
    cancelled: bool = False


class TaskQueueProtocol(Protocol):
    def initialize(self) -> None:
        ...

    def enqueue(self, job: Job) -> None:
        ...

    def dequeue(self) -> Job | None:
        ...

    def cancel(self, job_id: str) -> None:
        ...

    def shutdown(self) -> None:
        ...


class TaskQueue:
    """Priority queue with cancellation and retry support."""

    def __init__(self) -> None:
        self._heap: list[tuple[int, int, str, Job]] = []
        self._lock = threading.RLock()
        self._shutdown = False

    def initialize(self) -> None:
        logger.debug("Task queue initialized")

    def enqueue(self, job: Job) -> None:
        with self._lock:
            priority_value = int(job.priority)
            heapq.heappush(self._heap, (-priority_value, len(self._heap), job.id, job))
            logger.debug("Enqueued job %s", job.id)

    def dequeue(self) -> Job | None:
        with self._lock:
            if not self._heap:
                return None
            _, _, _, job = heapq.heappop(self._heap)
            return job

    def cancel(self, job_id: str) -> None:
        with self._lock:
            for _, _, _, job in self._heap:
                if job.id == job_id:
                    job.cancelled = True
                    job.status = JobStatus.CANCELLED
                    break

    def shutdown(self) -> None:
        with self._lock:
            self._shutdown = True
            logger.debug("Task queue shutdown")
