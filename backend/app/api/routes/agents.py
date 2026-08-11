"""Additive agentic, intelligence, memory, review, and insight endpoints."""

import re
import time
import uuid
from fastapi import APIRouter, HTTPException
from app.schemas.agents import AnalyzeDocumentRequest, CompareAgentRequest, ConversationCreate, ConversationRename, ResearchRequest, ReviewRequest
from app.services.agents.risk_agent import analyze_risks
from app.services.agents.retriever_agent import retrieve
from app.services.database import connection, now_iso
from app.services.document_intelligence import build_profile, get_profile
from app.services.agents.execution_store import recent_runs, remember_review

router = APIRouter()


@router.post("/agents/risk-analysis", tags=["Agents"])
def risk_analysis(request: ResearchRequest) -> dict:
    started = time.perf_counter()
    evidence = retrieve(request.question, request.document_ids)
    risks = analyze_risks(evidence)
    try:
        with connection() as db:
            for document_id in request.document_ids:
                db.execute("DELETE FROM document_risks WHERE document_id=?", (document_id,))
            for risk in risks:
                db.execute("INSERT INTO document_risks VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (str(uuid.uuid4()), risk.document_id, risk.title, risk.severity, risk.description,
                     risk.evidence, risk.recommendation, now_iso()))
    except Exception:
        pass
    run = {"id": str(uuid.uuid4()), "conversation_id": request.conversation_id, "agent_type": "risk-analysis",
        "status": "completed", "steps": 3, "tool_calls": 1, "retrieval_attempts": 1,
        "documents_examined": len({item["document_id"] for item in evidence}), "evidence_count": len(evidence),
        "critic_score": round(sum(item["score"] for item in evidence) / max(len(evidence), 1), 3),
        "latency_ms": int((time.perf_counter() - started) * 1000), "metadata": {}, "created_at": now_iso()}
    from app.services.agents.execution_store import remember_run
    remember_run(run)
    try:
        with connection() as db:
            metadata = "{}" if not db.postgres else __import__("psycopg.types.json", fromlist=["Jsonb"]).Jsonb({})
            db.execute("INSERT INTO agent_runs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (run["id"], run["conversation_id"], run["agent_type"], run["status"], run["steps"], run["tool_calls"],
                 run["retrieval_attempts"], run["documents_examined"], run["evidence_count"], run["critic_score"],
                 run["latency_ms"], metadata, run["created_at"]))
    except Exception:
        pass
    return {"risks": risks, "disclaimer": "AI risk analysis assists human review and is not legal or compliance advice."}


@router.post("/agents/analyze-document", tags=["Agents"])
def analyze_document(request: AnalyzeDocumentRequest) -> dict:
    document_id = request.document_id
    with connection() as db:
        row = db.execute("SELECT * FROM documents WHERE id=?", (document_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Document not found")
    return build_profile(str(row["id"]), row["content"], row["name"], row["department"])


@router.post("/agents/compare", tags=["Agents"])
def semantic_compare(request: CompareAgentRequest) -> dict:
    if request.document_a_id == request.document_b_id:
        raise HTTPException(400, "Choose two different documents.")
    with connection() as db:
        a = db.execute("SELECT * FROM documents WHERE id=?", (request.document_a_id,)).fetchone()
        b = db.execute("SELECT * FROM documents WHERE id=?", (request.document_b_id,)).fetchone()
    if not a or not b:
        raise HTTPException(404, "One or both documents were not found.")
    def lines(text: str) -> dict[str, str]:
        values = [x.strip() for x in re.split(r"(?<=[.!?])\s+|\n+", text) if len(x.strip()) > 25]
        return {re.sub(r"\W+", " ", x.lower()).strip(): x for x in values}
    left, right = lines(a["content"]), lines(b["content"])
    removed, added = list(left.keys() - right.keys())[:12], list(right.keys() - left.keys())[:12]
    risks = analyze_risks(retrieve("risk penalty obligation deadline", [request.document_a_id, request.document_b_id]))
    citations = [{"document_id": request.document_a_id, "document_name": a["name"], "excerpt": left[k]} for k in removed[:5]] + [{"document_id": request.document_b_id, "document_name": b["name"], "excerpt": right[k]} for k in added[:5]]
    return {"summary": f"Semantic review of {a['name']} and {b['name']} found {len(added)} additions and {len(removed)} removals in the bounded sample.",
        "major_changes": (added + removed)[:8], "added_content": [right[k] for k in added], "removed_content": [left[k] for k in removed],
        "changed_rules": [], "impact": ["Human review is recommended for changed obligations and deadlines."] if added or removed else [],
        "risks": [risk.model_dump() for risk in risks], "citations": citations}


@router.get("/agents/runs", tags=["Agents"])
def list_runs() -> list[dict]:
    stored: list[dict] = []
    try:
        with connection() as db:
            stored = [dict(row) for row in db.execute("SELECT * FROM agent_runs ORDER BY created_at DESC LIMIT 100").fetchall()]
    except Exception:
        pass
    combined = {item["id"]: item for item in [*recent_runs(), *stored]}
    return sorted(combined.values(), key=lambda item: str(item["created_at"]), reverse=True)[:100]


@router.get("/agents/runs/{run_id}", tags=["Agents"])
def get_run(run_id: str) -> dict:
    row = None
    try:
        with connection() as db:
            row = db.execute("SELECT * FROM agent_runs WHERE id=?", (run_id,)).fetchone()
    except Exception:
        pass
    if not row:
        fallback = next((item for item in recent_runs() if item["id"] == run_id), None)
        if fallback:
            return fallback
    if not row:
        raise HTTPException(404, "Agent run not found")
    return dict(row)


@router.get("/documents/{document_id}/intelligence", tags=["Document Intelligence"])
def document_intelligence(document_id: str) -> dict:
    profile = get_profile(document_id)
    if not profile:
        with connection() as db:
            row = db.execute("SELECT * FROM documents WHERE id=?", (document_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Document not found")
        profile = build_profile(document_id, row["content"], row["name"], row["department"])
    return profile


@router.get("/documents/{document_id}/risks", tags=["Document Intelligence"])
def document_risks(document_id: str) -> dict:
    return {"risks": analyze_risks(retrieve("risk penalty obligation deadline prohibited", [document_id])),
        "disclaimer": "AI risk analysis assists human review and is not legal or compliance advice."}


@router.post("/conversations", status_code=201, tags=["Conversations"])
def create_conversation(request: ConversationCreate) -> dict:
    item = {"id": str(uuid.uuid4()), "name": request.name, "summary": "", "created_at": now_iso(), "updated_at": now_iso()}
    with connection() as db: db.execute("INSERT INTO conversations VALUES (?, ?, ?, ?, ?)", tuple(item.values()))
    return item


@router.get("/conversations", tags=["Conversations"])
def conversations() -> list[dict]:
    with connection() as db: rows = db.execute("SELECT * FROM conversations ORDER BY updated_at DESC").fetchall()
    return [dict(row) for row in rows]


@router.get("/conversations/{conversation_id}", tags=["Conversations"])
def conversation(conversation_id: str) -> dict:
    with connection() as db:
        row = db.execute("SELECT * FROM conversations WHERE id=?", (conversation_id,)).fetchone()
        messages = db.execute("SELECT role,content,created_at FROM messages WHERE conversation_id=? ORDER BY created_at", (conversation_id,)).fetchall()
    if not row: raise HTTPException(404, "Conversation not found")
    return {**dict(row), "messages": [dict(message) for message in messages[-20:]]}


@router.patch("/conversations/{conversation_id}", tags=["Conversations"])
def rename_conversation(conversation_id: str, request: ConversationRename) -> dict:
    with connection() as db:
        row = db.execute("SELECT * FROM conversations WHERE id=?", (conversation_id,)).fetchone()
        if not row: raise HTTPException(404, "Conversation not found")
        db.execute("UPDATE conversations SET name=?,updated_at=? WHERE id=?", (request.name, now_iso(), conversation_id))
    return {"id": conversation_id, "name": request.name}


@router.delete("/conversations/{conversation_id}", status_code=204, tags=["Conversations"])
def delete_conversation(conversation_id: str) -> None:
    with connection() as db:
        db.execute("DELETE FROM messages WHERE conversation_id=?", (conversation_id,))
        db.execute("DELETE FROM conversations WHERE id=?", (conversation_id,))


@router.post("/ai-reviews", status_code=201, tags=["Human Review"])
def review(request: ReviewRequest) -> dict:
    item = {"id": str(uuid.uuid4()), "analysis_id": request.analysis_id, "status": "completed",
        "reviewer_action": request.action, "comment": request.comment, "created_at": now_iso()}
    remember_review(item)
    try:
        with connection() as db: db.execute("INSERT INTO ai_reviews VALUES (?, ?, ?, ?, ?, ?)", tuple(item.values()))
    except Exception:
        pass
    return item
