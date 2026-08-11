"""Validated public contracts for additive agentic features."""

from typing import Literal
from pydantic import BaseModel, Field


class ResearchRequest(BaseModel):
    question: str = Field(min_length=2, max_length=2000)
    document_ids: list[str] = Field(default_factory=list)
    conversation_id: str | None = None


class ResearchStep(BaseModel):
    order: int
    name: str
    status: Literal["pending", "completed", "skipped"] = "pending"


class Evidence(BaseModel):
    document_id: str
    document_name: str
    chunk_id: str
    excerpt: str
    score: float
    verified: bool = False


class CriticResult(BaseModel):
    passed: bool
    score: float
    unsupported_claims: list[str] = Field(default_factory=list)
    missing_citations: list[str] = Field(default_factory=list)
    contradictions: list[str] = Field(default_factory=list)
    recommendation: Literal["accept", "retry_retrieval", "regenerate", "insufficient_evidence"]


class Risk(BaseModel):
    title: str
    severity: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    description: str
    evidence: str
    document_id: str
    recommendation: str


class ResearchResult(BaseModel):
    run_id: str
    conversation_id: str
    status: str
    plan: list[ResearchStep]
    answer: str
    evidence: list[Evidence]
    risks: list[Risk]
    critic: CriticResult
    disclaimer: str | None = None


class CompareAgentRequest(BaseModel):
    document_a_id: str
    document_b_id: str


class AnalyzeDocumentRequest(BaseModel):
    document_id: str


class AnalyticsAgentRequest(BaseModel):
    question: str = Field(min_length=2, max_length=500)


class ReviewRequest(BaseModel):
    analysis_id: str
    action: Literal["approve", "reject", "request_reanalysis"]
    comment: str = Field(default="", max_length=2000)


class ConversationCreate(BaseModel):
    name: str = Field(default="New conversation", min_length=1, max_length=120)


class ConversationRename(BaseModel):
    name: str = Field(min_length=1, max_length=120)
