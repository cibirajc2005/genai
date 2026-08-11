from fastapi.testclient import TestClient
from app.main import app
from unittest.mock import patch
from app.services.agents.execution_store import remember_run

client = TestClient(app)


def test_remaining_agent_routes_validate_requests_and_list_runs():
    invalid = client.post("/api/agents/risk-analysis", json={"question":""})
    assert invalid.status_code == 422
    runs = client.get("/api/agents/runs")
    assert runs.status_code == 200
    assert isinstance(runs.json(), list)


def test_removed_agent_features_are_not_exposed():
    assert client.post("/api/agents/research", json={"question":"test"}).status_code == 404
    assert client.get("/api/insights").status_code == 404
    assert client.get("/api/knowledge-map").status_code == 404


def test_runs_use_memory_fallback_when_migration_is_not_installed():
    remember_run({"id":"fallback-run", "conversation_id":"c", "agent_type":"risk-analysis", "status":"completed",
        "steps":7, "tool_calls":4, "retrieval_attempts":1, "documents_examined":1,
        "evidence_count":2, "critic_score":.8, "latency_ms":10, "metadata":{}, "created_at":"2026-01-01"})
    with patch("app.api.routes.agents.connection", side_effect=RuntimeError("missing table")):
        response = client.get("/api/agents/runs")
    assert response.status_code == 200
    assert any(run["id"] == "fallback-run" for run in response.json())


def test_human_review_succeeds_without_optional_table():
    with patch("app.api.routes.agents.connection", side_effect=RuntimeError("missing table")):
        response = client.post("/api/ai-reviews", json={"analysis_id":"00000000-0000-0000-0000-000000000001", "action":"approve"})
    assert response.status_code == 201
