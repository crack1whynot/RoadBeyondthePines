"""Tests for the application-owned Runtime lifecycle."""

from __future__ import annotations

from fastapi.testclient import TestClient

from backend.app import main as app_main
from backend.core.di import create_app_container


def test_importing_or_creating_app_does_not_start_or_construct_runtime() -> None:
    # ``app`` is imported by this module, but its factory must remain inert
    # until ASGI lifespan starts.  A fresh factory result makes the assertion
    # independent of any other test's previous lifespan.
    application = app_main.create_app()

    assert getattr(application.state, "container", None) is None
    assert getattr(application.state, "runtime", None) is None


def test_lifespan_constructs_runtime_starts_it_and_reports_live_health(monkeypatch) -> None:
    container = create_app_container()
    assert container.runtime.running is False
    monkeypatch.setattr(app_main, "create_app_container", lambda: container)
    application = app_main.create_app()

    with TestClient(application) as client:
        assert application.state.container is container
        assert application.state.runtime is container.runtime
        assert container.runtime.running is True

        health = client.get("/health")
        assert health.status_code == 200
        body = health.json()
        assert body["status"] == "ok"
        assert body["components"]["runtime_running"] is True
        assert body["components"]["agents_loaded"] is True
        assert body["components"]["provider_manager_available"] is True

    assert container.runtime.running is False
