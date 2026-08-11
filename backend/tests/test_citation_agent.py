from app.services.agents.citation_agent import verify_citations


def test_citation_must_reference_a_real_chunk():
    rows = [{"document_id":"d", "document_name":"Doc", "chunk_id":"c", "text":"Evidence", "score":.8}]
    result = verify_citations("Claim [Source 1]", rows)
    assert result[0].verified
    assert result[0].chunk_id == "c"
