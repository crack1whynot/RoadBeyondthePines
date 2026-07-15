"""Shared execution-state primitives.

Execution state is deliberately separate from an agent's lifecycle state.  A
job/task can finish while its agent returns to ``IDLE``; conflating the two
made it impossible for callers to tell whether work actually succeeded.
"""

from __future__ import annotations

from enum import Enum


class ExecutionStatus(str, Enum):
    """Terminal and in-flight states for a unit of executable work."""

    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMED_OUT = "timed_out"

    @property
    def is_terminal(self) -> bool:
        """Return whether no further state transition is expected."""

        return self in {
            ExecutionStatus.SUCCEEDED,
            ExecutionStatus.FAILED,
            ExecutionStatus.CANCELLED,
            ExecutionStatus.TIMED_OUT,
        }
