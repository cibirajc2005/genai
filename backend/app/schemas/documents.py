from datetime import datetime
from pydantic import BaseModel, Field


class DocumentResponse(BaseModel):
    id: str
    name: str
    file_type: str
    size: int
    status: str
    department: str
    created_at: datetime
    chunk_count: int = 0
    vector_model: str | None = None


class ChatRequest(BaseModel):
    question: str = Field(min_length=2, max_length=2000)
    conversation_id: str | None = None
    document_ids: list[str] = Field(default_factory=list)


class Citation(BaseModel):
    document_id: str
    document_name: str
    excerpt: str
    score: float


class ChatResponse(BaseModel):
    answer: str
    conversation_id: str
    citations: list[Citation]
    confidence: str
    configured: bool


class CompareRequest(BaseModel):
    document_a_id: str
    document_b_id: str


class CompareResponse(BaseModel):
    comparison: str
    document_a: str
    document_b: str
    configured: bool
