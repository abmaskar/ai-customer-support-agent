from __future__ import annotations

from typing import Any

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    is_admin: bool = False


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    email: str
    is_admin: bool


class ChatRequest(BaseModel):
    message: str = Field(min_length=2)
    session_id: str | None = None


class FeedbackRequest(BaseModel):
    message_id: str
    vote: str


class MessageOut(BaseModel):
    id: str
    role: str
    content: str
    citations: list[dict[str, Any]] = []
    latency_ms: float | None = None
    grounded: bool = False


class ChatResponse(BaseModel):
    session_id: str
    message_id: str
    answer: str
    citations: list[dict[str, Any]]
    latency_ms: float
    grounded: bool
    backend_steps: list[str]


class DocumentOut(BaseModel):
    id: str
    filename: str
    title: str
    chunk_count: int
    created_at: str


class MetricsResponse(BaseModel):
    total_messages: int
    groundedness_rate: float
    fallback_rate: float
    feedback_up: int
    feedback_down: int
    p50_latency_ms: float
    p95_latency_ms: float
    estimated_cost_usd: float
    documents_count: int
    sessions_count: int
    release_gate: dict[str, Any]
