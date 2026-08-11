from unittest.mock import patch
from app.services.agents.self_correcting_rag import retrieve_verified


def test_weak_evidence_retries_and_deduplicates():
    weak = [{"chunk_id": "1", "score": .1}]
    improved = [{"chunk_id": "1", "score": .6}, {"chunk_id": "2", "score": .5}]
    with patch("app.services.agents.self_correcting_rag.retrieve", side_effect=[weak, improved, []]):
        evidence, attempts = retrieve_verified("notice period", [])
    assert attempts <= 3
    assert [item["chunk_id"] for item in evidence] == ["1", "2"]
