"""Safe domain errors for orchestration use cases."""

from __future__ import annotations


class OrchestrationError(Exception):
    """Base error that is safe to map to an API response."""

    code = "orchestration_error"


class InvalidOrchestrationRequestError(OrchestrationError):
    """Raised when an orchestration request has no usable text."""

    code = "invalid_request"


class UnsupportedRequestError(OrchestrationError):
    """Raised when Phase 0 has no honest executor for an intent."""

    code = "unsupported_request"


class RuntimeUnavailableError(OrchestrationError):
    """Raised when the runtime cannot accept execution work."""

    code = "runtime_unavailable"
