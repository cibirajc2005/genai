"""Additive agentic, intelligence, memory, review, and insight endpoints."""

import json
import re
import uuid
from fastapi import APIRouter, HTTPException
from app.schemas.agents import AnalyzeDocumentRequest, AnalyticsAgentRequest, CompareAgentRequest, ConversationCreate, ConversationRename, ResearchRequest, ResearchResult, ReviewRequest
from app.services.agents.analytics_agent import answer_analytics
from app.services.agents.orchestrator import run_research
from app.services.agents.risk_agent import analyze_risks
from app.services.agents.retriever_agent import retrieve
from app.services.database import connection, now_iso
from app.services.document_intelligence import build_profile, get_profile

router = APIRouter()


@router.post("/agents/research", response_model=ResearchResult, tags=["Agents"])
def research(request: ResearchRequest) -> ResearchResult:
    try:
        return run_research(request.question, request.document_ids, request.conversation_id)
    except RuntimeError as exc:
        raise HTTPException(503, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(502, "Research agent could not complete safely.") from exc


@router.post("/agents/verify-answer", tags=["Agents"])
def verify_answer(request: ResearchRequest) -> dict:
    result = run_research(request.question, request.document_ids, request.conversation_id)
    return {"run_id": result.run_id, "critic": result.critic, "citations": result.evidence}


@router.post("/agents/risk-analysis", tags=["Agents"])
def risk_analysis(request: ResearchRequest) -> dict:
    evidence = retrieve(request.question, request.document_ids)
    risks = analyze_risks(evidence)
    with connection() as db:
        for document_id in request.document_ids:
            db.execute("DELETE FROM document_risks WHERE document_id=?", (document_id,))
        for risk in risks:
            db.execute("INSERT INTO document_risks VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (str(uuid.uuid4()), risk.document_id, risk.title, risk.severity, risk.description,
                 risk.evidence, risk.recommendation, now_iso()))
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


@router.post("/agents/analytics", tags=["Agents"])
def analytics_agent(request: AnalyticsAgentRequest) -> dict:
    return answer_analytics(request.question)


@router.get("/agents/runs", tags=["Agents"])
def list_runs() -> list[dict]:
    with connection() as db:
        rows = db.execute("SELECT * FROM agent_runs ORDER BY created_at DESC LIMIT 100").fetchall()
    return [dict(row) for row in rows]


@router.get("/agents/runs/{run_id}", tags=["Agents"])
def get_run(run_id: str) -> dict:
    with connection() as db:
        row = db.execute("SELECT * FROM agent_runs WHERE id=?", (run_id,)).fetchone()
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


@router.get("/insights", tags=["Insights"])
def insights() -> list[dict]:
    with connection() as db:
        documents = db.execute("SELECT id,name,department,content FROM documents ORDER BY created_at DESC LIMIT 20").fetchall()
    output = []
    for document in documents:
        risks = analyze_risks(retrieve("risk penalty obligation deadline", [str(document["id"])]))
        if risks:
            risk = risks[0]
            output.append({"category": "Risk", "title": risk.title, "description": risk.description,
                "severity": risk.severity, "evidence": risk.evidence, "document_id": str(document["id"]), "document_name": document["name"]})
    return output[:12]


@router.get("/knowledge-map", tags=["Insights"])
def knowledge_map() -> dict:
    with connection() as db:
        documents = db.execute("SELECT id,name,department FROM documents").fetchall()
        profiles = db.execute("SELECT document_id,topics,entities,risks FROM document_intelligence").fetchall()
    nodes, links = [], []
    seen = set()
    for doc in documents:
        doc_id = str(doc["id"]); nodes.append({"id": doc_id, "label": doc["name"], "type": "document"}); seen.add(doc_id)
        dept_id = f"department:{doc['department']}"
        if dept_id not in seen: nodes.append({"id": dept_id, "label": doc["department"], "type": "department"}); seen.add(dept_id)
        links.append({"source": doc_id, "target": dept_id})
    for profile in profiles:
        for topic in (json.loads(profile["topics"]) if isinstance(profile["topics"], str) else profile["topics"])[:6]:
            node_id = f"topic:{topic}"
            if node_id not in seen: nodes.append({"id": node_id, "label": topic, "type": "topic"}); seen.add(node_id)
            links.append({"source": str(profile["document_id"]), "target": node_id})
    return {"nodes": nodes, "links": links}


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
    with connection() as db: db.execute("INSERT INTO ai_reviews VALUES (?, ?, ?, ?, ?, ?)", tuple(item.values()))
    return item
