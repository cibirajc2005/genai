"""Document management, analytics, and grounded chat endpoints."""

import re
import json
import time
import uuid
import tempfile
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.core.config import settings
from app.schemas.documents import ChatRequest, ChatResponse, Citation, CompareRequest, CompareResponse, DocumentResponse
from app.services.database import connection, now_iso
from app.services.documents import ALLOWED_EXTENSIONS, MAX_FILE_SIZE, chunks, extract_text, safe_filename
from app.services.embeddings import EmbeddingService, cosine_similarity
from app.services.llm.openai_client import OpenAIConfigurationError, OpenAIService
from app.services.storage import delete_document_file, store_document

router = APIRouter()


def _document(row) -> DocumentResponse:
    keys = set(row.keys())
    values = {key: row[key] for key in DocumentResponse.model_fields if key in keys}
    if "id" in values:
        values["id"] = str(values["id"])
    return DocumentResponse(**values)


@router.get("/documents", response_model=list[DocumentResponse], tags=["Documents"])
def list_documents(search: str = "") -> list[DocumentResponse]:
    with connection() as db:
        if search:
            rows = db.execute("""SELECT d.*, COUNT(c.id) chunk_count, MAX(c.vector_model) vector_model
                FROM documents d LEFT JOIN chunks c ON c.document_id=d.id WHERE d.name LIKE ?
                GROUP BY d.id ORDER BY d.created_at DESC""", (f"%{search}%",)).fetchall()
        else:
            rows = db.execute("""SELECT d.*, COUNT(c.id) chunk_count, MAX(c.vector_model) vector_model
                FROM documents d LEFT JOIN chunks c ON c.document_id=d.id
                GROUP BY d.id ORDER BY d.created_at DESC""").fetchall()
    return [_document(row) for row in rows]


@router.post("/documents/upload", response_model=DocumentResponse, status_code=201, tags=["Documents"])
async def upload_document(file: UploadFile = File(...), department: str = Form("General")) -> DocumentResponse:
    filename = safe_filename(file.filename or "document")
    suffix = Path(filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, "Only PDF, DOCX, TXT, and MD files are supported.")
    content = await file.read(MAX_FILE_SIZE + 1)
    if not content:
        raise HTTPException(400, "The uploaded file is empty.")
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(413, "The maximum file size is 20 MB.")
    document_id = str(uuid.uuid4())
    if settings.supabase_enabled:
        # Vercel Functions only provide writable temporary storage under /tmp.
        path = Path(tempfile.gettempdir()) / f"{document_id}_{filename}"
    else:
        settings.documents_path.mkdir(parents=True, exist_ok=True)
        path = settings.documents_path / f"{document_id}_{filename}"
    path.write_bytes(content)
    try:
        text = extract_text(path).strip()
        if not text:
            raise ValueError("No readable text was found in this file.")
    except Exception as exc:
        path.unlink(missing_ok=True)
        raise HTTPException(400, f"Document extraction failed: {exc}") from exc
    created = now_iso()
    text_chunks = chunks(text)
    vectors, vector_model = EmbeddingService().embed(text_chunks)
    stored_path = store_document(path, f"{document_id}/{filename}")
    with connection() as db:
        db.execute("INSERT INTO documents VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                   (document_id, filename, suffix[1:].upper(), len(content), "Indexed", department[:80], text, stored_path, created))
        db.executemany("INSERT INTO chunks VALUES (?, ?, ?, ?, ?, ?, ?)", [
            (str(uuid.uuid4()), document_id, index, chunk, json.dumps(vector), vector_model, created)
            for index, (chunk, vector) in enumerate(zip(text_chunks, vectors))
        ])
        row = db.execute("""SELECT d.*, COUNT(c.id) chunk_count, MAX(c.vector_model) vector_model
            FROM documents d LEFT JOIN chunks c ON c.document_id=d.id WHERE d.id=? GROUP BY d.id""", (document_id,)).fetchone()
    if settings.agentic_ai_enabled:
        try:
            from app.services.document_intelligence import build_profile
            build_profile(document_id, text, filename, department[:80])
        except Exception:
            # Intelligence is optional and must never make a successful upload fail.
            pass
    return _document(row)


@router.get("/documents/{document_id}", tags=["Documents"])
def get_document(document_id: str) -> dict:
    with connection() as db:
        row = db.execute("SELECT * FROM documents WHERE id = ?", (document_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Document not found")
    result = dict(row)
    result["preview"] = result.pop("content")[:5000]
    result.pop("path", None)
    with connection() as db:
        result["chunks"] = [dict(chunk) for chunk in db.execute(
            "SELECT id, chunk_index, content, vector_model FROM chunks WHERE document_id=? ORDER BY chunk_index", (document_id,)
        ).fetchall()]
    return result


@router.delete("/documents/{document_id}", status_code=204, tags=["Documents"])
def delete_document(document_id: str) -> None:
    with connection() as db:
        row = db.execute("SELECT path FROM documents WHERE id = ?", (document_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Document not found")
        db.execute("DELETE FROM chunks WHERE document_id = ?", (document_id,))
        db.execute("DELETE FROM documents WHERE id = ?", (document_id,))
    delete_document_file(row["path"])


def _retrieve(question: str, document_ids: list[str]) -> list[dict]:
    terms = {word for word in re.findall(r"[a-z0-9]{3,}", question.lower()) if word not in {"what", "this", "that", "with", "from", "about"}}
    with connection() as db:
        if document_ids:
            placeholders = ",".join("?" for _ in document_ids)
            rows = db.execute(f"""SELECT c.*,d.name FROM chunks c JOIN documents d ON d.id=c.document_id
                WHERE c.document_id IN ({placeholders})""", document_ids).fetchall()
        else:
            rows = db.execute("SELECT c.*,d.name FROM chunks c JOIN documents d ON d.id=c.document_id").fetchall()
    if not rows:
        return []
    models = {row["vector_model"] for row in rows}
    query_vectors: dict[str, list[float]] = {}
    for model in models:
        if model == "local-hash-384":
            from app.services.embeddings import local_embedding
            query_vectors[model] = local_embedding(question)
        else:
            vector, actual_model = EmbeddingService().embed([question])
            query_vectors[model] = vector[0] if actual_model == model else []
    ranked = []
    for row in rows:
        text = row["content"]
        keyword = sum(text.lower().count(term) for term in terms) / max(1, len(terms))
        semantic = cosine_similarity(query_vectors.get(row["vector_model"], []), json.loads(row["vector"]))
        score = max(0.0, semantic) * .75 + min(keyword, 1.0) * .25
        if score > 0:
            ranked.append({"row": {"id": str(row["document_id"]), "name": row["name"]}, "text": text, "score": score})
    return sorted(ranked, key=lambda item: item["score"], reverse=True)[:5]


@router.post("/documents/compare", response_model=CompareResponse, tags=["Documents"])
def compare_documents(request: CompareRequest) -> CompareResponse:
    if request.document_a_id == request.document_b_id:
        raise HTTPException(400, "Choose two different documents.")
    with connection() as db:
        first = db.execute("SELECT * FROM documents WHERE id=?", (request.document_a_id,)).fetchone()
        second = db.execute("SELECT * FROM documents WHERE id=?", (request.document_b_id,)).fetchone()
    if not first or not second:
        raise HTTPException(404, "One or both documents were not found.")
    def local_comparison() -> str:
        def sentences(text: str) -> list[str]:
            return [part.strip() for part in re.split(r"(?<=[.!?])\s+|\n+", text) if len(part.strip()) > 35]
        first_sentences, second_sentences = sentences(first["content"]), sentences(second["content"])
        first_keys = {re.sub(r"\W+", " ", sentence.lower()).strip(): sentence for sentence in first_sentences}
        second_keys = {re.sub(r"\W+", " ", sentence.lower()).strip(): sentence for sentence in second_sentences}
        only_first = [first_keys[key] for key in first_keys.keys() - second_keys.keys()][:8]
        only_second = [second_keys[key] for key in second_keys.keys() - first_keys.keys()][:8]
        removed = "\n".join(f"• {item}" for item in only_first) or "• No distinct passages detected."
        added = "\n".join(f"• {item}" for item in only_second) or "• No distinct passages detected."
        return (f"Overview\nCompared {first['name']} with {second['name']} using extracted text.\n\n"
                f"Content unique to {first['name']}\n{removed}\n\n"
                f"Content unique to {second['name']}\n{added}\n\n"
                "Note\nThis offline comparison reports textual differences. Configure OpenAI for a semantic policy-impact analysis.")

    configured = True
    try:
        comparison = OpenAIService().compare_documents(first["name"], first["content"], second["name"], second["content"])
    except OpenAIConfigurationError:
        configured = False
        comparison = local_comparison()
    except Exception:
        configured = False
        comparison = local_comparison()
    with connection() as db:
        db.execute("""INSERT INTO comparisons
            (id, document_a_id, document_b_id, document_a_name, document_b_name, comparison, configured, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)""", (
            str(uuid.uuid4()), request.document_a_id, request.document_b_id,
            first["name"], second["name"], comparison, int(configured), now_iso()
        ))
    return CompareResponse(comparison=comparison, document_a=first["name"], document_b=second["name"], configured=configured)


@router.post("/chat", response_model=ChatResponse, tags=["AI Assistant"])
def chat(request: ChatRequest) -> ChatResponse:
    started = time.perf_counter()
    conversation_id = request.conversation_id or str(uuid.uuid4())
    evidence = _retrieve(request.question, request.document_ids)
    citations = [Citation(document_id=item["row"]["id"], document_name=item["row"]["name"],
                          excerpt=item["text"][:280], score=round(min(item["score"], 1.0), 2)) for item in evidence]
    configured = True
    if not evidence:
        answer = "I couldn't find sufficient information in the uploaded documents to answer this confidently."
        confidence = "LOW"
    else:
        context = "\n\n".join(f"[Source {i}] {item['row']['name']}\n{item['text']}" for i, item in enumerate(evidence, 1))
        try:
            answer = OpenAIService().generate_answer(request.question, context)
            confidence = "HIGH" if len(evidence) >= 2 else "MEDIUM"
        except OpenAIConfigurationError as exc:
            configured = False
            answer = f"{exc} I found {len(evidence)} relevant source(s), shown below."
            confidence = "LOW"
        except Exception as exc:
            raise HTTPException(502, f"OpenAI request failed: {exc}") from exc
    elapsed = int((time.perf_counter() - started) * 1000)
    with connection() as db:
        db.execute("INSERT INTO messages (conversation_id, role, content, created_at) VALUES (?, ?, ?, ?)",
                   (conversation_id, "user", request.question, now_iso()))
        db.execute("INSERT INTO messages (conversation_id, role, content, created_at) VALUES (?, ?, ?, ?)",
                   (conversation_id, "assistant", answer, now_iso()))
        db.execute("INSERT INTO query_logs (question, successful, latency_ms, created_at) VALUES (?, ?, ?, ?)",
                   (request.question, int(bool(evidence) and configured), elapsed, now_iso()))
    return ChatResponse(answer=answer, conversation_id=conversation_id, citations=citations,
                        confidence=confidence, configured=configured)


@router.get("/analytics", tags=["Analytics"])
def analytics() -> dict:
    with connection() as db:
        documents = db.execute("SELECT COUNT(*) AS value FROM documents").fetchone()["value"]
        queries = db.execute("SELECT COUNT(*) AS value FROM query_logs").fetchone()["value"]
        successful = db.execute("SELECT COUNT(*) AS value FROM query_logs WHERE successful = 1").fetchone()["value"]
        average = db.execute("SELECT COALESCE(AVG(latency_ms), 0) AS value FROM query_logs").fetchone()["value"]
    return {"total_documents": documents, "indexed_documents": documents, "total_queries": queries,
            "successful_answers": successful, "average_response_time_ms": round(average)}
