"""Bounded local intelligence extraction; never invents facts absent from text."""

import json
import re
import uuid
from collections import Counter
from app.services.database import connection, now_iso


def build_profile(document_id: str, text: str, name: str, department: str = "General") -> dict:
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+", text) if len(s.strip()) > 20]
    words = [w for w in re.findall(r"[A-Za-z]{4,}", text.lower()) if w not in {"this", "that", "with", "from", "shall", "will", "have"}]
    topics = [word for word, _ in Counter(words).most_common(8)]
    dates = list(dict.fromkeys(re.findall(r"\b(?:\d{1,2}[/-])?(?:\d{1,2}[/-])?\d{4}\b|\b(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{1,2}(?:,\s*\d{4})?", text, re.I)))[:20]
    obligations = [s for s in sentences if re.search(r"\b(must|shall|required|responsible)\b", s, re.I)][:10]
    risks = [s for s in sentences if re.search(r"\b(risk|penalty|terminate|liable|prohibited|violation)\b", s, re.I)][:10]
    actions = [s for s in sentences if re.search(r"\b(review|submit|complete|notify|approve|report)\b", s, re.I)][:10]
    entities = list(dict.fromkeys(re.findall(r"\b[A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+){1,3}\b", text)))[:20]
    lowered = f"{name} {text[:1000]}".lower()
    doc_type = next((label for key, label in (("policy", "Policy"), ("contract", "Contract"), ("report", "Report"), ("handbook", "Handbook")) if key in lowered), "Document")
    profile = {"document_id": document_id, "document_type": doc_type, "department": department,
        "summary": " ".join(sentences[:3])[:1200] or name, "topics": topics, "entities": entities,
        "important_dates": dates, "obligations": obligations, "risks": risks, "action_items": actions,
        "keywords": topics, "sensitivity_level": "Review required" if risks else "Standard"}
    timestamp = now_iso()
    try:
        with connection() as db:
            db.execute("DELETE FROM document_intelligence WHERE document_id=?", (document_id,))
            values = [topics, entities, dates, obligations, risks, actions]
            if db.postgres:
                from psycopg.types.json import Jsonb
                values = [Jsonb(value) for value in values]
            else:
                values = [json.dumps(value) for value in values]
            db.execute("INSERT INTO document_intelligence VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (str(uuid.uuid4()), document_id, profile["summary"], doc_type, *values, timestamp, timestamp))
    except Exception:
        # Intelligence remains available in the response before migrations run.
        pass
    return profile


def get_profile(document_id: str) -> dict | None:
    try:
        with connection() as db:
            row = db.execute("SELECT * FROM document_intelligence WHERE document_id=?", (document_id,)).fetchone()
    except Exception:
        return None
    if not row:
        return None
    result = dict(row)
    for key in ("topics", "entities", "dates", "obligations", "risks", "action_items"):
        result[key] = json.loads(result[key]) if isinstance(result[key], str) else result[key]
    return result
