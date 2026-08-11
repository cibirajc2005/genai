from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_agent_routes_validate_requests_and_list_runs():
    invalid = client.post("/api/agents/research", json={"question":""})
    assert invalid.status_code == 422
    runs = client.get("/api/agents/runs")
    assert runs.status_code == 200
    assert isinstance(runs.json(), list)


def test_analytics_route_rejects_arbitrary_empty_question():
    response = client.post("/api/agents/analytics", json={"question":""})
    assert response.status_code == 422
