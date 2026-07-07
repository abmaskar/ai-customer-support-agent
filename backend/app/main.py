from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from fastapi import FastAPI, File, HTTPException, UploadFile
from pydantic import BaseModel, Field

try:
    from pypdf import PdfReader
except Exception:  # pragma: no cover
    PdfReader = None


app = FastAPI(title="AI Customer Support Agent", version="1.0.0")


@dataclass
class DocumentChunk:
    doc_id: str
    title: str
    source: str
    content: str


@dataclass
class Store:
    chunks: List[DocumentChunk] = field(default_factory=list)
    conversations: Dict[str, List[dict]] = field(default_factory=dict)
    feedback: List[dict] = field(default_factory=list)


store = Store()


class ChatRequest(BaseModel):
    message: str = Field(min_length=2)
    session_id: Optional[str] = None


class FeedbackRequest(BaseModel):
    session_id: str
    message_id: str
    vote: str  # up/down


def _tokenize(text: str) -> set[str]:
    return {t for t in re.findall(r"[a-zA-Z0-9_]+", text.lower()) if len(t) > 2}


def _extract_text(file: UploadFile, payload: bytes) -> str:
    if file.filename and file.filename.lower().endswith(".pdf"):
        if PdfReader is None:
            raise HTTPException(status_code=400, detail="pypdf not installed for PDF parsing.")
        reader = PdfReader(file.file)
        return "\n".join(page.extract_text() or "" for page in reader.pages).strip()
    return payload.decode("utf-8", errors="ignore")


def _search_docs(query: str, top_k: int = 3) -> List[DocumentChunk]:
    q = _tokenize(query)
    ranked: List[tuple[int, DocumentChunk]] = []
    for c in store.chunks:
        overlap = len(q & _tokenize(c.content))
        if overlap > 0:
            ranked.append((overlap, c))
    ranked.sort(key=lambda x: x[0], reverse=True)
    return [item[1] for item in ranked[:top_k]]


@app.get("/health")
def health() -> dict:
    return {"ok": True, "documents": len(store.chunks), "sessions": len(store.conversations)}


@app.post("/api/admin/upload")
async def admin_upload(file: UploadFile = File(...)) -> dict:
    payload = await file.read()
    if not payload:
        raise HTTPException(status_code=400, detail="Empty file.")
    text = _extract_text(file, payload)
    if not text.strip():
        raise HTTPException(status_code=400, detail="No text extracted.")

    doc_id = str(uuid.uuid4())
    # Simple chunking by paragraph for demo.
    parts = [p.strip() for p in text.split("\n\n") if p.strip()]
    if not parts:
        parts = [text.strip()]
    for part in parts:
        store.chunks.append(
            DocumentChunk(doc_id=doc_id, title=file.filename or "uploaded", source=file.filename or "uploaded", content=part)
        )
    return {"doc_id": doc_id, "chunks_created": len(parts), "filename": file.filename}


@app.post("/api/chat")
def chat(req: ChatRequest) -> dict:
    session_id = req.session_id or str(uuid.uuid4())
    hits = _search_docs(req.message)
    if hits:
        answer = (
            "Based on company documents: "
            + " ".join(h.content[:240] for h in hits)
            + " ..."
        )
        citations = [{"source": h.source, "preview": h.content[:120]} for h in hits]
    else:
        answer = "I could not find relevant content in uploaded docs. Please upload policy/product docs."
        citations = []

    message_id = str(uuid.uuid4())
    thread = store.conversations.setdefault(session_id, [])
    thread.append({"role": "user", "text": req.message})
    thread.append({"role": "assistant", "text": answer, "message_id": message_id, "citations": citations})
    return {"session_id": session_id, "message_id": message_id, "answer": answer, "citations": citations}


@app.get("/api/chat/history/{session_id}")
def chat_history(session_id: str) -> dict:
    return {"session_id": session_id, "messages": store.conversations.get(session_id, [])}


@app.post("/api/chat/feedback")
def chat_feedback(req: FeedbackRequest) -> dict:
    vote = req.vote.lower()
    if vote not in {"up", "down"}:
        raise HTTPException(status_code=400, detail="vote must be 'up' or 'down'")
    store.feedback.append(req.model_dump())
    return {"saved": True, "feedback_count": len(store.feedback)}

