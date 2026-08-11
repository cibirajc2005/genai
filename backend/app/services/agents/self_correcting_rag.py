from app.core.config import settings
from app.services.query_expansion import expand_query
from app.services.agents.retriever_agent import retrieve


def retrieve_verified(question: str, document_ids: list[str]) -> tuple[list[dict], int]:
    best = retrieve(question, document_ids)
    attempts = 1
    if best and best[0]["score"] >= .35:
        return best, attempts
    merged = {item["chunk_id"]: item for item in best}
    for expanded in expand_query(question)[1:1 + settings.agent_max_retrieval_retries]:
        attempts += 1
        for item in retrieve(expanded, document_ids):
            previous = merged.get(item["chunk_id"])
            if not previous or item["score"] > previous["score"]:
                merged[item["chunk_id"]] = item
    return sorted(merged.values(), key=lambda x: x["score"], reverse=True)[:8], attempts
