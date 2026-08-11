import re
from app.schemas.agents import Evidence


def verify_citations(answer: str, evidence: list[dict]) -> list[Evidence]:
    cited = {int(n) for n in re.findall(r"\[Source (\d+)\]", answer)}
    return [Evidence(document_id=item["document_id"], document_name=item["document_name"],
        chunk_id=item["chunk_id"], excerpt=item["text"][:320], score=round(min(item["score"], 1), 3),
        verified=(index in cited and item["score"] >= .2)) for index, item in enumerate(evidence, 1)]
