from __future__ import annotations

import time
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.llm import generate_answer
from app.models import ChatSession, Feedback, Message, User
from app.rag import rag_service
from app.schemas import ChatRequest, ChatResponse, FeedbackRequest, MessageOut

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
def chat(
    req: ChatRequest,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User | None, Depends(get_current_user)] = None,
) -> ChatResponse:
    steps: list[str] = []
    start = time.perf_counter()

    session_id = req.session_id
    if session_id:
        session = db.get(ChatSession, session_id)
        if session is None:
            raise HTTPException(status_code=404, detail="Session not found")
    else:
        session = ChatSession(user_id=user.id if user else None)
        db.add(session)
        db.commit()
        db.refresh(session)
        session_id = session.id

    steps.append("1) Saved user message to PostgreSQL")
    user_msg = Message(session_id=session_id, role="user", content=req.message)
    db.add(user_msg)

    steps.append("2) Embedded query and searched Qdrant vector DB")
    hits = rag_service.search(req.message, top_k=3)

    steps.append(f"3) Retrieved {len(hits)} relevant chunks")
    llm_result = generate_answer(req.message, hits)
    steps.append(f"4) Generated answer via {('OpenAI' if hits else 'fallback')} LLM provider")

    citations = [
        {"source": h.get("source", "doc"), "preview": h.get("content", "")[:160], "score": h.get("score")}
        for h in hits
    ]
    grounded = len(hits) > 0 and "could not find" not in llm_result["answer"].lower()
    latency_ms = round((time.perf_counter() - start) * 1000, 2)

    message_id = str(uuid.uuid4())
    assistant_msg = Message(
        id=message_id,
        session_id=session_id,
        role="assistant",
        content=llm_result["answer"],
        citations=citations,
        latency_ms=latency_ms,
        token_count=llm_result["token_count"],
        cost_usd=llm_result["cost_usd"],
        grounded=grounded,
    )
    db.add(assistant_msg)
    db.commit()

    steps.append("5) Stored assistant response + citations + metrics in PostgreSQL")

    return ChatResponse(
        session_id=session_id,
        message_id=message_id,
        answer=llm_result["answer"],
        citations=citations,
        latency_ms=latency_ms,
        grounded=grounded,
        backend_steps=steps,
    )


@router.get("/history/{session_id}")
def history(session_id: str, db: Annotated[Session, Depends(get_db)]) -> dict:
    messages = (
        db.query(Message)
        .filter(Message.session_id == session_id)
        .order_by(Message.created_at.asc())
        .all()
    )
    return {
        "session_id": session_id,
        "messages": [
            MessageOut(
                id=m.id,
                role=m.role,
                content=m.content,
                citations=m.citations or [],
                latency_ms=m.latency_ms,
                grounded=m.grounded,
            ).model_dump()
            for m in messages
        ],
    }


@router.post("/feedback")
def feedback(req: FeedbackRequest, db: Annotated[Session, Depends(get_db)]) -> dict:
    vote = req.vote.lower()
    if vote not in {"up", "down"}:
        raise HTTPException(status_code=400, detail="vote must be 'up' or 'down'")
    msg = db.get(Message, req.message_id)
    if msg is None:
        raise HTTPException(status_code=404, detail="Message not found")
    db.add(Feedback(message_id=req.message_id, vote=vote))
    db.commit()
    return {"saved": True, "message_id": req.message_id, "vote": vote}
