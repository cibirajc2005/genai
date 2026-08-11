"""Bounded research orchestration with retrieval, risk, citation, and critic stages."""

import json
import time
import uuid
from app.core.config import settings
from app.schemas.agents import ResearchResult
from app.services.database import connection, now_iso
from app.services.llm.openai_client import OpenAIConfigurationError, OpenAIService
from app.services.agents.planner import create_plan
from app.services.agents.self_correcting_rag import retrieve_verified
from app.services.agents.citation_agent import verify_citations
from app.services.agents.critic_agent import critique
from app.services.agents.risk_agent import analyze_risks

INSUFFICIENT = "Insufficient evidence was found in the uploaded documents."


def run_research(question: str, document_ids: list[str], conversation_id: str | None = None) -> ResearchResult:
    if not settings.agentic_ai_enabled:
        raise RuntimeError("Agentic AI features are disabled.")
    started = time.perf_counter()
    run_id, conversation_id = str(uuid.uuid4()), conversation_id or str(uuid.uuid4())
    plan = create_plan()
    evidence, attempts = retrieve_verified(question, document_ids)
    risks = analyze_risks(evidence)
    if not evidence or evidence[0]["score"] < .12:
        answer, configured = INSUFFICIENT, False
    else:
        context = "\n\n".join(f"[Source {i}] {e['document_name']}\n{e['text']}" for i, e in enumerate(evidence, 1))
        try:
            answer = OpenAIService().generate_answer(question, context)
            configured = True
        except (OpenAIConfigurationError, Exception):
            configured = False
            answer = "Evidence found:\n" + "\n".join(f"[Source {i}] {e['text'][:260]}" for i, e in enumerate(evidence[:4], 1))
    verified = verify_citations(answer, evidence)
    critic = critique(answer, verified)
    for step in plan:
        step.status = "completed"
    elapsed = int((time.perf_counter() - started) * 1000)
    metadata = {"configured": configured, "limits": {"steps": settings.agent_max_steps, "tool_calls": settings.agent_max_tool_calls}}
    with connection() as db:
        if db.postgres:
            from psycopg.types.json import Jsonb
            stored_metadata = Jsonb(metadata)
        else:
            stored_metadata = json.dumps(metadata)
        db.execute("INSERT INTO agent_runs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (run_id, conversation_id, "research", "completed", len(plan), min(6, settings.agent_max_tool_calls), attempts,
             len({e['document_id'] for e in evidence}), len(evidence), critic.score, elapsed, stored_metadata, now_iso()))
    return ResearchResult(run_id=run_id, conversation_id=conversation_id, status="Completed", plan=plan,
        answer=answer, evidence=verified, risks=risks, critic=critic,
        disclaimer="AI risk analysis assists human review and is not legal or compliance advice." if risks else None)
