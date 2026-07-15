from __future__ import annotations

from typing import Any, Protocol

from backend.runtime.task_queue import Job, JobPriority, JobResult, JobStatus


class JobHandler(Protocol):
    """Contract for handling a job."""

    def handle(self, job: Job) -> JobResult:
        ...


class BaseJobHandler:
    """Base class for job handlers.

    It intentionally does not fabricate a success result.  Concrete handlers
    must perform work and return a truthful :class:`JobResult` (or a value the
    worker can normalize).
    """

    def handle(self, job: Job) -> JobResult:
        raise NotImplementedError("Concrete job handlers must implement handle(job)")
