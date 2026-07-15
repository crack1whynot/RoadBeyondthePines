from __future__ import annotations

from typing import Any, Protocol

from backend.runtime.task_queue import Job, JobPriority, JobResult, JobStatus


class JobHandler(Protocol):
    """Contract for handling a job."""

    def handle(self, job: Job) -> JobResult:
        ...


class BaseJobHandler:
    """Base implementation for job handlers."""

    def handle(self, job: Job) -> JobResult:
        return JobResult(success=True, payload={"job_id": job.id, "name": job.name})
