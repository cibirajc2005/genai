import re
from app.schemas.agents import CriticResult, Evidence


def critique(answer: str, evidence: list[Evidence]) -> CriticResult:
    citations = re.findall(r"\[Source \d+\]", answer)
    supported = bool(evidence) and bool(citations)
    score = min(1.0, (sum(item.score for item in evidence) / max(len(evidence), 1)) * .7 + (.3 if supported else 0))
    if not evidence:
        recommendation = "insufficient_evidence"
    elif not citations:
        recommendation = "regenerate"
    elif score < .45:
        recommendation = "retry_retrieval"
    else:
        recommendation = "accept"
    return CriticResult(passed=recommendation == "accept", score=round(score, 3),
        unsupported_claims=[] if supported else ["Answer lacks verifiable source references"],
        missing_citations=[] if citations else ["Major claims require citations"], contradictions=[], recommendation=recommendation)
