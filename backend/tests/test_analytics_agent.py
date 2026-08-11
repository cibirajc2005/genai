from app.services.agents.analytics_agent import answer_analytics


def test_analytics_uses_allowlisted_document_count():
    result = answer_analytics("How many documents do we have?")
    assert result["visualization"] == "number"
    assert result["data"][0]["label"] == "Documents"
