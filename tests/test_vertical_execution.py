"""ASGI coverage for the supported Brain-to-Runtime diagnostic path."""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

from backend.app import main as app_main
from backend.core.di import create_app_container
from backend.memory.memory import InMemoryStore, ProjectMemory


def _application_with_temporary_memory(monkeypatch, tmp_path):
    """Build a real container while keeping execution summaries out of ``data/``."""

    container = create_app_container()
    memory = ProjectMemory(
        store=InMemoryStore(),
        storage_path=str(tmp_path / "execution-memory.json"),
    )
    container.memory = memory
    container.development_request_service.memory = memory
    monkeypatch.setattr(app_main, "create_app_container", lambda: container)
    return app_main.create_app(), container


def test_brain_execute_runs_actual_diagnostic_payload_and_persists_summary(monkeypatch, tmp_path) -> None:
    application, container = _application_with_temporary_memory(monkeypatch, tmp_path)

    with TestClient(application) as client:
        response = client.post("/brain/execute", json={"request_text": "diagnostic: pine-road"})

        assert response.status_code == 200
        body = response.json()
        result = body["execution"]["results"]["results"][0]
        assert result["success"] is True
        assert result["status"] == "succeeded"
        assert result["agent_id"] == "DiagnosticAgent"
        assert result["output"] == "pine-road"
        assert result["output"] != "Handled task"
        assert body["warnings"] == []
        assert body["metadata"]["memory_persisted"] is True

        entries = container.memory.list_entries()
        assert len(entries) == 1
        assert entries[0].source == "development_request_service"
        summary = json.loads(entries[0].content)
        assert summary["execution_plan"]["status"] == "succeeded"
        assert summary["task_results"][0]["success"] is True
        assert "pine-road" in summary["task_results"][0]["output"]

    assert container.runtime.running is False
    assert (tmp_path / "execution-memory.json").exists()


def test_brain_execute_returns_explicit_error_for_unsupported_request(monkeypatch, tmp_path) -> None:
    application, container = _application_with_temporary_memory(monkeypatch, tmp_path)

    with TestClient(application) as client:
        response = client.post(
            "/brain/execute",
            json={"request_text": "create a production Unreal gameplay system"},
        )

    assert response.status_code == 422
    assert response.json()["detail"] == "Phase 0 supports only explicit diagnostic or echo requests"
    assert container.memory.list_entries() == []
    assert container.runtime.running is False


def test_execution_returns_payload_but_redacts_secret_shaped_values_from_memory(monkeypatch, tmp_path) -> None:
    application, container = _application_with_temporary_memory(monkeypatch, tmp_path)
    original_create_plan = container.planner.create_plan

    def secret_payload_plan(request_text: str):
        plan = original_create_plan(request_text)
        plan.tasks[0].parameters = {
            "payload": {"api_key": "never-store-this-value", "label": "safe-value"}
        }
        return plan

    monkeypatch.setattr(container.planner, "create_plan", secret_payload_plan)

    with TestClient(application) as client:
        response = client.post("/brain/execute", json={"request_text": "diagnostic: secrets"})

    assert response.status_code == 200
    assert response.json()["execution"]["results"]["results"][0]["output"] == {
        "api_key": "never-store-this-value",
        "label": "safe-value",
    }
    stored_summary = container.memory.list_entries()[0].content
    assert "never-store-this-value" not in stored_summary
    assert "[REDACTED]" in stored_summary
    assert "safe-value" in stored_summary
