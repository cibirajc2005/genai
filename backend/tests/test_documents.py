"""End-to-end tests for the first usable knowledge workflow."""

from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_upload_retrieve_chat_and_delete() -> None:
    uploaded = client.post(
        "/api/documents/upload",
        files={"file": ("leave-policy.txt", b"Employees receive twenty days of annual leave each year.", "text/plain")},
        data={"department": "Human Resources"},
    )
    assert uploaded.status_code == 201
    document = uploaded.json()
    assert document["status"] == "Indexed"

    try:
        with patch("app.api.routes.documents.OpenAIService.generate_answer", return_value="Employees receive twenty days. [Source 1]"):
            answer = client.post("/api/chat", json={"question": "How many annual leave days?", "document_ids": [document["id"]]})
        assert answer.status_code == 200
        result = answer.json()
        assert result["citations"][0]["document_name"] == "leave-policy.txt"
    finally:
        deleted = client.delete(f"/api/documents/{document['id']}")
        assert deleted.status_code == 204
