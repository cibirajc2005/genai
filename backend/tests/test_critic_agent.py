from app.schemas.agents import Evidence
from app.services.agents.critic_agent import critique


def test_critic_rejects_missing_citations():
    evidence = [Evidence(document_id="d", document_name="Doc", chunk_id="c", excerpt="Policy", score=.9, verified=False)]
    result = critique("An unsupported answer", evidence)
    assert not result.passed
    assert result.recommendation == "regenerate"
