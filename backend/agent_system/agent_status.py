from __future__ import annotations

from enum import Enum


class AgentStatus(str, Enum):
    """Lifecycle states for agents."""

    IDLE = "idle"
    BUSY = "busy"
    PAUSED = "paused"
    OFFLINE = "offline"
    ERROR = "error"
    INITIALIZING = "initializing"
    STOPPING = "stopping"
