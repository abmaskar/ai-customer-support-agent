from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models import ChatSession, Document, Feedback, Message
from app.schemas import MetricsResponse

router = APIRouter(prefix="/api/metrics", tags=["metrics"])
settings = get_settings()


def _percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    sorted_vals = sorted(values)
    idx = int(round((p / 100) * (len(sorted_vals) - 1)))
    return round(sorted_vals[idx], 2)


@router.get("", response_model=MetricsResponse)
def get_metrics(db: Annotated[Session, Depends(get_db)]) -> MetricsResponse:
    total_messages = db.query(Message).filter(Message.role == "assistant").count()
    grounded_count = db.query(Message).filter(Message.role == "assistant", Message.grounded.is_(True)).count()
    fallback_count = total_messages - grounded_count

    latencies = [
        float(x[0])
        for x in db.query(Message.latency_ms)
        .filter(Message.role == "assistant", Message.latency_ms.isnot(None))
        .all()
        if x[0] is not None
    ]

    feedback_up = db.query(Feedback).filter(Feedback.vote == "up").count()
    feedback_down = db.query(Feedback).filter(Feedback.vote == "down").count()
    cost = db.query(func.coalesce(func.sum(Message.cost_usd), 0.0)).scalar() or 0.0

    groundedness = round(grounded_count / max(total_messages, 1), 3)
    fallback_rate = round(fallback_count / max(total_messages, 1), 3)
    p50 = _percentile(latencies, 50)
    p95 = _percentile(latencies, 95)

    checks = {
        "groundedness_ok": groundedness >= settings.eval_groundedness_target,
        "fallback_ok": fallback_rate <= settings.fallback_rate_target,
        "latency_ok": p95 <= settings.p95_latency_target_ms,
    }
    release_gate = {
        "status": "GO" if all(checks.values()) else "NO_GO",
        "checks": checks,
        "targets": {
            "groundedness": settings.eval_groundedness_target,
            "fallback_rate": settings.fallback_rate_target,
            "p95_latency_ms": settings.p95_latency_target_ms,
        },
    }

    return MetricsResponse(
        total_messages=total_messages,
        groundedness_rate=groundedness,
        fallback_rate=fallback_rate,
        feedback_up=feedback_up,
        feedback_down=feedback_down,
        p50_latency_ms=p50,
        p95_latency_ms=p95,
        estimated_cost_usd=round(float(cost), 6),
        documents_count=db.query(Document).count(),
        sessions_count=db.query(ChatSession).count(),
        release_gate=release_gate,
    )
