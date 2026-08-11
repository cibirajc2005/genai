"""Additive retrieval agent retaining semantic + keyword ranking."""

import json
import re
from app.services.database import connection
from app.services.embeddings import EmbeddingService, cosine_similarity, local_embedding


def retrieve(question: str, document_ids: list[str], limit: int = 8) -> list[dict]:
    terms = {w for w in re.findall(r"[a-z0-9]{3,}", question.lower()) if w not in {"what", "that", "this", "with", "from", "about"}}
    with connection() as db:
        if document_ids:
            marks = ",".join("?" for _ in document_ids)
            rows = db.execute(f"SELECT c.*,d.name FROM chunks c JOIN documents d ON d.id=c.document_id WHERE c.document_id IN ({marks})", document_ids).fetchall()
        else:
            rows = db.execute("SELECT c.*,d.name FROM chunks c JOIN documents d ON d.id=c.document_id").fetchall()
    query_vectors: dict[str, list[float]] = {}
    for model in {row["vector_model"] for row in rows}:
        if model == "local-hash-384":
            query_vectors[model] = local_embedding(question)
        else:
            vectors, actual = EmbeddingService().embed([question])
            query_vectors[model] = vectors[0] if actual == model else []
    ranked = []
    for row in rows:
        keyword = sum(row["content"].lower().count(term) for term in terms) / max(1, len(terms))
        semantic = cosine_similarity(query_vectors.get(row["vector_model"], []), json.loads(row["vector"]))
        score = max(semantic, 0) * .75 + min(keyword, 1) * .25
        if score > 0:
            ranked.append({"chunk_id": str(row["id"]), "document_id": str(row["document_id"]), "document_name": row["name"], "text": row["content"], "score": score})
    return sorted(ranked, key=lambda x: x["score"], reverse=True)[:limit]
