from __future__ import annotations

import threading
import time
from typing import Any, Protocol

from backend.core.logging import get_logger
from backend.runtime.task_queue import Job, JobStatus, TaskQueue

logger = get_logger("runtime.worker")


class WorkerProtocol(Protocol):
    def start(self) -> None:
        ...

    def stop(self) -> None:
        ...

    def attach_task_queue(self, queue: TaskQueue) -> None:
        ...


class Worker:
    """Background worker for processing queued jobs."""

    def __init__(self) -> None:
        self._queue: TaskQueue | None = None
        self._running = False
        self._thread: threading.Thread | None = None

    def attach_task_queue(self, queue: TaskQueue) -> None:
        self._queue = queue

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        logger.info("Worker started")

    def stop(self) -> None:
        self._running = False
        logger.info("Worker stopped")

    def _run_loop(self) -> None:
        while self._running:
            if self._queue is None:
                time.sleep(0.1)
                continue
            job = self._queue.dequeue()
            if job is None:
                time.sleep(0.1)
                continue
            if job.cancelled:
                job.status = JobStatus.CANCELLED
                continue
            job.status = JobStatus.RUNNING
            logger.info("Processing job %s", job.id)
            job.status = JobStatus.COMPLETED
            job.progress = 1.0
            time.sleep(0.01)
