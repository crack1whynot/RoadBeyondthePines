"""Focused tests for the truthful in-process Runtime execution boundary."""

from __future__ import annotations

import threading

import pytest

from backend.core.execution import ExecutionStatus
from backend.runtime.runtime import Runtime
from backend.runtime.task_queue import Job


def test_runtime_executes_registered_handler_and_persists_actual_result() -> None:
    runtime = Runtime()
    runtime.register_handler(
        "echo",
        lambda job: {
            "success": True,
            "status": ExecutionStatus.SUCCEEDED,
            "output": {"echo": job.payload["payload"]},
            "metadata": {"handler": "echo"},
        },
    )
    runtime.start()
    try:
        job = runtime.enqueue_job(Job(name="echo", payload={"payload": "pipeline"}))
        result = runtime.wait_for_job(job.id, timeout=1.0)

        assert result is not None
        assert result.success is True
        assert result.status is ExecutionStatus.SUCCEEDED
        assert result.output == {"echo": "pipeline"}
        assert runtime.get_job(job.id) is job
        assert runtime.get_job_result(job.id) is result
    finally:
        runtime.stop()


def test_runtime_records_safe_failure_when_handler_raises() -> None:
    runtime = Runtime()

    def broken_handler(_: Job) -> None:
        raise RuntimeError("internal implementation detail")

    runtime.register_handler("broken", broken_handler)
    runtime.start()
    try:
        job = runtime.enqueue_job(Job(name="broken"))
        result = runtime.wait_for_job(job.id, timeout=1.0)

        assert result is not None
        assert result.success is False
        assert result.status is ExecutionStatus.FAILED
        assert result.error_code == "HANDLER_EXCEPTION"
        assert "internal implementation detail" not in (result.error or "")
    finally:
        runtime.stop()


def test_runtime_fails_job_without_registered_handler() -> None:
    runtime = Runtime()
    runtime.start()
    try:
        job = runtime.enqueue_job(Job(name="missing-handler"))
        result = runtime.wait_for_job(job.id, timeout=1.0)

        assert result is not None
        assert result.success is False
        assert result.status is ExecutionStatus.FAILED
        assert result.error_code == "HANDLER_NOT_FOUND"
    finally:
        runtime.stop()


def test_runtime_records_timeout_without_fabricating_success() -> None:
    runtime = Runtime()
    release_handler = threading.Event()

    def blocked_handler(_: Job) -> dict[str, object]:
        release_handler.wait(timeout=1.0)
        return {"success": True, "output": "late result"}

    runtime.register_handler("blocked", blocked_handler)
    runtime.start()
    try:
        job = runtime.enqueue_job(Job(name="blocked", timeout_seconds=0.01))
        result = runtime.wait_for_job(job.id, timeout=1.0)

        assert result is not None
        assert result.success is False
        assert result.status is ExecutionStatus.TIMED_OUT
        assert result.error_code == "JOB_TIMEOUT"
    finally:
        release_handler.set()
        runtime.stop()


def test_runtime_cancels_running_job() -> None:
    runtime = Runtime()
    handler_started = threading.Event()
    release_handler = threading.Event()

    def cancellable_handler(_: Job) -> dict[str, object]:
        handler_started.set()
        release_handler.wait(timeout=1.0)
        return {"success": True, "output": "should not be returned"}

    runtime.register_handler("cancellable", cancellable_handler)
    runtime.start()
    try:
        job = runtime.enqueue_job(Job(name="cancellable"))
        assert handler_started.wait(timeout=1.0)
        assert runtime.cancel_job(job.id) is True

        result = runtime.wait_for_job(job.id, timeout=1.0)
        assert result is not None
        assert result.success is False
        assert result.status is ExecutionStatus.CANCELLED
        assert result.error_code == "JOB_CANCELLED"
    finally:
        release_handler.set()
        runtime.stop()


def test_runtime_stop_joins_worker_can_restart_and_queue_rejects_after_shutdown() -> None:
    runtime = Runtime()
    runtime.register_handler("echo", lambda job: {"success": True, "output": job.payload})
    runtime.start()
    assert runtime.running is True

    runtime.stop()
    assert runtime.running is False
    with pytest.raises(RuntimeError, match="shut down"):
        runtime.context.task_queue.enqueue(Job(name="echo"))

    runtime.start()
    try:
        restarted_job = runtime.enqueue_job(Job(name="echo", payload={"restart": True}))
        result = runtime.wait_for_job(restarted_job.id, timeout=1.0)

        assert runtime.running is True
        assert result is not None
        assert result.status is ExecutionStatus.SUCCEEDED
        assert result.output == {"restart": True}
    finally:
        runtime.stop()
