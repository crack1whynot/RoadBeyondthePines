"""Optional stdlib HTTP transport for a future Unreal Editor bridge.

The transport deliberately has no network side effects at import or construction
time.  A small HTTP client is created only for the first bridge request and can
be replaced with a fake client or sender in tests.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
import inspect
import json
import math
import socket
from typing import Any, Protocol, TypeAlias, runtime_checkable
from urllib import error as urllib_error
from urllib import request as urllib_request
from urllib.parse import urlsplit

from pydantic import ValidationError

from backend.core.logging import get_logger
from backend.mcp.errors import (
    MCPConnectionError,
    MCPError,
    MCPNotConnectedError,
    MCPProtocolError,
    MCPTimeoutError,
    MCPTransportError,
)
from backend.mcp.models import (
    MCPCommand,
    MCPCommandResult,
    MCPHealthStatus,
    UnrealConnectionInfo,
)
from backend.mcp.transport import UnrealTransport

logger = get_logger(__name__)


JSONValue: TypeAlias = dict[str, Any] | list[Any] | str | int | float | bool | None


@dataclass(frozen=True, slots=True)
class HTTPRequest:
    """One bridge HTTP request, suitable for deterministic fake senders."""

    method: str
    url: str
    headers: Mapping[str, str]
    body: bytes | None
    timeout_seconds: float
    json_body: JSONValue = None


@dataclass(slots=True)
class HTTPResponse:
    """Minimal HTTP response shape returned by an injectable client or sender."""

    status: int
    body: bytes | str | JSONValue = b""
    headers: Mapping[str, str] = field(default_factory=dict)


@runtime_checkable
class HTTPClient(Protocol):
    """Synchronous or asynchronous HTTP client used only by this transport."""

    def request(self, request: HTTPRequest) -> Any:
        """Send a request and return an :class:`HTTPResponse`-compatible value."""

    def close(self) -> Any:
        """Release client resources, if any."""


HTTPClientFactory: TypeAlias = Callable[[], HTTPClient]
HTTPRequestSender: TypeAlias = Callable[..., Any]


class _NoRedirectHandler(urllib_request.HTTPRedirectHandler):
    """Reject redirects so an Authorization header cannot cross an origin."""

    def redirect_request(
        self,
        request: urllib_request.Request,
        response: Any,
        code: int,
        _: str,
        headers: Any,
        __: str,
    ) -> None:
        raise urllib_error.HTTPError(
            request.full_url,
            code,
            "Unreal bridge redirects are not permitted",
            headers,
            response,
        )


class _UrllibHTTPClient:
    """Stateless stdlib client; each request is performed in a worker thread."""

    def request(self, request: HTTPRequest) -> HTTPResponse:
        native_request = urllib_request.Request(
            request.url,
            data=request.body,
            headers=dict(request.headers),
            method=request.method,
        )
        opener = urllib_request.build_opener(_NoRedirectHandler())
        with opener.open(native_request, timeout=request.timeout_seconds) as response:
            return HTTPResponse(
                status=response.getcode(),
                body=response.read(),
                headers=dict(response.headers.items()),
            )

    def close(self) -> None:
        """urllib has no persistent session to close."""


class _SenderHTTPClient:
    """Adapter that turns a small fake sender function into an HTTP client."""

    def __init__(self, sender: HTTPRequestSender) -> None:
        self._sender = sender

    def request(self, request: HTTPRequest) -> Any:
        return _call_http_callable(self._sender, request)

    def close(self) -> Any:
        close = getattr(self._sender, "close", None)
        if callable(close):
            return close()
        return None


def _call_http_callable(callable_object: Callable[..., Any], request: HTTPRequest) -> Any:
    """Invoke common fake-client signatures without requiring a third-party SDK.

    The documented form is ``sender(request: HTTPRequest)``.  Keyword and
    positional forms are also accepted so a conventional lightweight fake client
    can be injected without an adapter.
    """

    try:
        signature = inspect.signature(callable_object)
    except (TypeError, ValueError):
        return callable_object(request)

    attempts: tuple[tuple[tuple[Any, ...], dict[str, Any]], ...] = (
        ((request,), {}),
        (
            (),
            {
                "method": request.method,
                "url": request.url,
                "headers": dict(request.headers),
                "body": request.body,
                "timeout_seconds": request.timeout_seconds,
            },
        ),
        (
            (),
            {
                "method": request.method,
                "url": request.url,
                "headers": dict(request.headers),
                "data": request.body,
                "timeout": request.timeout_seconds,
            },
        ),
        (
            (),
            {
                "method": request.method,
                "url": request.url,
                "headers": dict(request.headers),
                "json": request.json_body,
                "timeout": request.timeout_seconds,
            },
        ),
        (
            (
                request.method,
                request.url,
                dict(request.headers),
                request.body,
                request.timeout_seconds,
            ),
            {},
        ),
    )
    for args, kwargs in attempts:
        try:
            signature.bind(*args, **kwargs)
        except TypeError:
            continue
        return callable_object(*args, **kwargs)
    raise TypeError("Injected HTTP sender has an unsupported request signature")


class HTTPUnrealTransport(UnrealTransport):
    """HTTP implementation of :class:`UnrealTransport` for an Editor bridge.

    ``settings`` may be the application settings object.  Explicit keyword
    arguments take precedence and keep this transport simple to construct in
    isolated tests.  ``sender`` and ``http_client`` are deliberately injectable;
    neither causes a request until one of the async transport methods is called.
    """

    def __init__(
        self,
        settings: object | None = None,
        *,
        host: str | None = None,
        port: int | None = None,
        base_url: str | None = None,
        timeout_seconds: float | None = None,
        auth_token: object | None = None,
        sender: HTTPRequestSender | None = None,
        request_sender: HTTPRequestSender | None = None,
        http_sender: HTTPRequestSender | None = None,
        http_client: HTTPClient | object | None = None,
        client_factory: HTTPClientFactory | None = None,
    ) -> None:
        injected_senders = [
            candidate
            for candidate in (sender, request_sender, http_sender)
            if candidate is not None
        ]
        if len(injected_senders) > 1:
            raise ValueError("Provide only one HTTP sender")
        if http_client is not None and (injected_senders or client_factory is not None):
            raise ValueError("Provide either an HTTP client, sender, or client factory")

        resolved_host = (
            host
            if host is not None
            else _setting(settings, "unreal_mcp_host", "127.0.0.1")
        )
        resolved_port = port if port is not None else _setting(settings, "unreal_mcp_port", 8765)
        resolved_base_url = (
            base_url
            if base_url is not None
            else _setting(settings, "unreal_mcp_base_url", "")
        )
        resolved_timeout = (
            timeout_seconds
            if timeout_seconds is not None
            else _setting(settings, "unreal_mcp_timeout_seconds", 10.0)
        )
        resolved_token = (
            auth_token
            if auth_token is not None
            else _setting(settings, "unreal_mcp_auth_token", None)
        )

        self._base_url = _normalize_base_url(
            base_url=resolved_base_url,
            host=str(resolved_host),
            port=resolved_port,
        )
        self._timeout_seconds = _normalize_timeout(resolved_timeout)
        self._auth_token = _secret_text(resolved_token)
        self._connected = False
        self._connection_info: UnrealConnectionInfo | None = None
        self._client: HTTPClient | object | None = None

        if http_client is not None:
            self._client_factory: Callable[[], HTTPClient | object] = lambda: http_client
        elif injected_senders:
            selected_sender = injected_senders[0]
            self._client_factory = lambda: _SenderHTTPClient(selected_sender)
        elif client_factory is not None:
            self._client_factory = client_factory
        else:
            self._client_factory = _UrllibHTTPClient

    @classmethod
    def from_settings(
        cls,
        settings: object,
        *,
        sender: HTTPRequestSender | None = None,
        http_client: HTTPClient | object | None = None,
        client_factory: HTTPClientFactory | None = None,
    ) -> "HTTPUnrealTransport":
        """Build a transport from application settings without connecting."""
        return cls(
            settings,
            sender=sender,
            http_client=http_client,
            client_factory=client_factory,
        )

    @property
    def base_url(self) -> str:
        """Return the non-secret bridge URL used by this transport."""
        return self._base_url

    @property
    def timeout_seconds(self) -> float:
        """Return the configured maximum duration of one bridge request."""
        return self._timeout_seconds

    async def connect(self) -> UnrealConnectionInfo:
        """Query the bridge connection endpoint and cache its public metadata."""
        payload = await self._request_json("GET", "/connection")
        info = self._parse_connection_info(payload)
        self._connection_info = info
        self._connected = info.connected
        return info

    async def disconnect(self) -> None:
        """Mark disconnected and close an already-created client, if it has one."""
        client = self._client
        self._client = None
        self._connected = False
        if self._connection_info is not None:
            self._connection_info = self._connection_info.model_copy(update={"connected": False})

        if client is None:
            return
        try:
            await self._close_client(client)
        except (OSError, RuntimeError, TypeError, ValueError) as error:
            logger.debug("Unable to close Unreal MCP HTTP client")
            raise MCPTransportError("Unable to close the Unreal bridge HTTP client") from error

    async def is_connected(self) -> bool:
        """Return the connection state most recently reported by the bridge."""
        return self._connected

    async def execute(self, command: MCPCommand) -> MCPCommandResult:
        """POST one already-authorized command to the future bridge protocol."""
        if not self._connected:
            raise MCPNotConnectedError("Unreal MCP transport is not connected")

        payload = {
            "id": command.id,
            "name": command.name,
            "arguments": command.arguments,
            "timeout_seconds": command.timeout_seconds,
            "metadata": command.metadata,
            "read_only": command.read_only,
        }
        response = await self._request_json(
            "POST",
            "/commands",
            payload=payload,
            timeout_seconds=command.timeout_seconds,
        )
        return self._parse_command_result(response, command)

    async def health_check(self) -> MCPHealthStatus:
        """GET the bridge health endpoint and update cached connection state."""
        payload = await self._request_json("GET", "/health")
        status = self._parse_health_status(payload)
        self._connected = status.connected
        return status

    def get_name(self) -> str:
        """Return the stable transport registry name."""
        return "http"

    def get_capabilities(self) -> list[str]:
        """Return capabilities last supplied by the bridge connection response."""
        if self._connection_info is None:
            return []
        return list(self._connection_info.capabilities)

    async def _request_json(
        self,
        method: str,
        path: str,
        *,
        payload: JSONValue = None,
        timeout_seconds: float | None = None,
    ) -> JSONValue:
        timeout = (
            self._timeout_seconds
            if timeout_seconds is None
            else _normalize_timeout(timeout_seconds)
        )
        body = (
            None
            if payload is None
            else json.dumps(payload, separators=(",", ":")).encode("utf-8")
        )
        headers = {"Accept": "application/json"}
        if body is not None:
            headers["Content-Type"] = "application/json"
        if self._auth_token:
            headers["Authorization"] = f"Bearer {self._auth_token}"

        request = HTTPRequest(
            method=method,
            url=f"{self._base_url}{path}",
            headers=headers,
            body=body,
            timeout_seconds=timeout,
            json_body=payload,
        )
        response = await self._send_request(request)
        if response.status < 200 or response.status >= 300:
            retryable = response.status >= 500
            raise MCPTransportError(
                f"Unreal bridge returned HTTP status {response.status}",
                retryable=retryable,
                details={"status": response.status},
            )
        return _decode_json_body(response.body)

    async def _send_request(self, request: HTTPRequest) -> HTTPResponse:
        """Send one request and normalize network-level failures into MCP errors."""
        try:
            raw_response = await asyncio.wait_for(
                self._invoke_client(request), timeout=request.timeout_seconds
            )
        except MCPError:
            raise
        except asyncio.TimeoutError as error:
            logger.debug("Unreal MCP HTTP request timed out")
            raise MCPTimeoutError("Unreal bridge request timed out") from error
        except (TimeoutError, socket.timeout) as error:
            logger.debug("Unreal MCP HTTP request timed out")
            raise MCPTimeoutError("Unreal bridge request timed out") from error
        except urllib_error.HTTPError as error:
            retryable = error.code >= 500
            raise MCPTransportError(
                f"Unreal bridge returned HTTP status {error.code}",
                retryable=retryable,
                details={"status": error.code},
            ) from error
        except urllib_error.URLError as error:
            if isinstance(error.reason, (TimeoutError, socket.timeout)):
                logger.debug("Unreal MCP HTTP request timed out")
                raise MCPTimeoutError("Unreal bridge request timed out") from error
            logger.debug("Unable to reach Unreal MCP HTTP bridge")
            raise MCPConnectionError("Unable to reach the Unreal bridge") from error
        except (ConnectionError, OSError) as error:
            logger.debug("Unable to reach Unreal MCP HTTP bridge")
            raise MCPConnectionError("Unable to reach the Unreal bridge") from error
        except (TypeError, ValueError, RuntimeError) as error:
            logger.debug("Unreal MCP HTTP transport request failed")
            raise MCPTransportError("Unreal bridge HTTP transport failed") from error

        try:
            return _coerce_http_response(raw_response)
        except (TypeError, ValueError) as error:
            raise MCPProtocolError("Unreal bridge returned an invalid HTTP response") from error

    async def _invoke_client(self, request: HTTPRequest) -> Any:
        client = self._get_or_create_client()
        request_method = getattr(client, "request", None)
        if not callable(request_method):
            if not callable(client):
                raise TypeError("HTTP client does not provide a request method")
            request_method = client

        if inspect.iscoroutinefunction(request_method):
            return await _call_http_callable(request_method, request)

        result = await asyncio.to_thread(_call_http_callable, request_method, request)
        if inspect.isawaitable(result):
            return await result
        return result

    def _get_or_create_client(self) -> HTTPClient | object:
        if self._client is None:
            self._client = self._client_factory()
        return self._client

    async def _close_client(self, client: HTTPClient | object) -> None:
        async_close = getattr(client, "aclose", None)
        if callable(async_close):
            result = async_close()
            if inspect.isawaitable(result):
                await result
            return

        close = getattr(client, "close", None)
        if not callable(close):
            return
        if inspect.iscoroutinefunction(close):
            await close()
            return
        result = await asyncio.to_thread(close)
        if inspect.isawaitable(result):
            await result

    def _parse_connection_info(self, payload: JSONValue) -> UnrealConnectionInfo:
        data = _unwrap_mapping(payload, "connection")
        data["transport"] = self.get_name()
        try:
            return UnrealConnectionInfo.model_validate(data)
        except ValidationError as error:
            raise MCPProtocolError(
                "Unreal bridge returned invalid connection information"
            ) from error

    def _parse_health_status(self, payload: JSONValue) -> MCPHealthStatus:
        data = _unwrap_mapping(payload, "health")
        try:
            return MCPHealthStatus.model_validate(data)
        except ValidationError as error:
            raise MCPProtocolError("Unreal bridge returned invalid health information") from error

    @staticmethod
    def _parse_command_result(payload: JSONValue, command: MCPCommand) -> MCPCommandResult:
        data = _unwrap_mapping(payload, "result")
        data["command_id"] = command.id
        try:
            return MCPCommandResult.model_validate(data)
        except ValidationError as error:
            raise MCPProtocolError("Unreal bridge returned an invalid command result") from error


# A conventional spelling alias keeps factories and external callers flexible.
HttpUnrealTransport = HTTPUnrealTransport


def _setting(settings: object | None, name: str, default: Any) -> Any:
    if settings is None:
        return default
    value = getattr(settings, name, default)
    return default if value is None else value


def _normalize_base_url(*, base_url: object, host: str, port: object) -> str:
    candidate = str(base_url).strip() if base_url else ""
    if not candidate:
        try:
            numeric_port = int(port)
        except (TypeError, ValueError) as error:
            raise ValueError("Unreal MCP port must be an integer") from error
        if not 1 <= numeric_port <= 65535:
            raise ValueError("Unreal MCP port must be between 1 and 65535")
        candidate = f"http://{host.strip()}:{numeric_port}"

    normalized = candidate.rstrip("/")
    parsed = urlsplit(normalized)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("Unreal MCP base URL must be an absolute HTTP(S) URL")
    return normalized


def _normalize_timeout(value: object) -> float:
    try:
        timeout = float(value)
    except (TypeError, ValueError) as error:
        raise ValueError("Unreal MCP timeout must be a positive number") from error
    if not math.isfinite(timeout) or timeout <= 0:
        raise ValueError("Unreal MCP timeout must be a positive finite number")
    return timeout


def _secret_text(value: object | None) -> str | None:
    """Extract a SecretStr-like value without exposing it outside this module."""
    if value is None:
        return None
    get_secret_value = getattr(value, "get_secret_value", None)
    if callable(get_secret_value):
        value = get_secret_value()
    text = str(value).strip()
    return text or None


def _coerce_http_response(value: Any) -> HTTPResponse:
    if isinstance(value, HTTPResponse):
        return value
    if isinstance(value, Mapping):
        if "status" in value or "status_code" in value:
            status = value.get("status", value.get("status_code"))
            body = value.get("body", value.get("json", value.get("data", b"")))
            headers = value.get("headers", {})
            return HTTPResponse(status=int(status), body=body, headers=_safe_headers(headers))
        return HTTPResponse(status=200, body=dict(value))
    if isinstance(value, tuple):
        if len(value) == 2:
            status, body = value
            return HTTPResponse(status=int(status), body=body)
        if len(value) == 3:
            status, headers, body = value
            return HTTPResponse(status=int(status), body=body, headers=_safe_headers(headers))
        raise ValueError("HTTP response tuple must contain status and body")

    status = getattr(value, "status", getattr(value, "status_code", None))
    if status is None:
        raise TypeError("HTTP response does not have a status")
    headers = _safe_headers(getattr(value, "headers", {}))
    if hasattr(value, "body"):
        body = value.body
    elif hasattr(value, "content"):
        body = value.content
    elif callable(getattr(value, "json", None)):
        body = value.json()
    elif callable(getattr(value, "read", None)):
        body = value.read()
    else:
        body = b""
    return HTTPResponse(status=int(status), body=body, headers=headers)


def _safe_headers(value: object) -> dict[str, str]:
    if not isinstance(value, Mapping):
        return {}
    return {str(key): str(item) for key, item in value.items()}


def _decode_json_body(body: bytes | str | JSONValue) -> JSONValue:
    if isinstance(body, (dict, list, int, float, bool)) or body is None:
        return body
    if isinstance(body, bytes):
        try:
            text = body.decode("utf-8")
        except UnicodeDecodeError as error:
            raise MCPProtocolError("Unreal bridge returned non-UTF-8 JSON") from error
    elif isinstance(body, str):
        text = body
    else:
        raise MCPProtocolError("Unreal bridge returned an invalid JSON body")
    if not text.strip():
        raise MCPProtocolError("Unreal bridge returned an empty JSON body")
    try:
        return json.loads(text)
    except json.JSONDecodeError as error:
        raise MCPProtocolError("Unreal bridge returned invalid JSON") from error


def _unwrap_mapping(payload: JSONValue, wrapper_key: str) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        raise MCPProtocolError("Unreal bridge returned an invalid JSON object")
    if isinstance(payload.get(wrapper_key), Mapping):
        return dict(payload[wrapper_key])
    if isinstance(payload.get("data"), Mapping) and wrapper_key in {"connection", "health"}:
        return dict(payload["data"])
    return dict(payload)
