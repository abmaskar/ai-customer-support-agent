from __future__ import annotations

import logging
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_ollama import ChatOllama

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

SYSTEM_PROMPT = """You are a helpful customer support agent.
Answer ONLY using the provided context from company documents.
If the context is insufficient, say you could not find the answer in company docs.
Always be concise and professional."""


def _estimate_cost(tokens: int) -> float:
    # gpt-4o-mini rough estimate; Ollama local = ~0
    if settings.default_provider == "openai":
        return round((tokens / 1000) * 0.00015, 6)
    return 0.0


def generate_answer(question: str, context_chunks: list[dict[str, Any]]) -> dict[str, Any]:
    context = "\n\n".join(
        f"[Source: {c.get('source', 'doc')}]\n{c.get('content', '')}" for c in context_chunks
    )
    user_prompt = f"Context:\n{context}\n\nQuestion: {question}\n\nAnswer:"

    if settings.default_provider == "openai" and settings.openai_api_key:
        from langchain_openai import ChatOpenAI

        llm = ChatOpenAI(
            model=settings.openai_model,
            api_key=settings.openai_api_key.get_secret_value(),
            temperature=settings.temperature,
            max_tokens=settings.max_tokens,
        )
    else:
        llm = ChatOllama(
            model=settings.ollama_model,
            base_url=settings.ollama_base_url,
            temperature=settings.temperature,
        )

    messages = [SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=user_prompt)]
    try:
        response = llm.invoke(messages)
        text = response.content if isinstance(response.content, str) else str(response.content)
        usage = getattr(response, "usage_metadata", None) or {}
        tokens = int(usage.get("total_tokens", max(len(text.split()), 1) * 2))
    except Exception as exc:
        logger.warning("LLM call failed (%s), using extractive fallback", exc)
        if context_chunks:
            text = "Based on company documents: " + " ".join(c["content"][:200] for c in context_chunks)
        else:
            text = "I could not find relevant content in uploaded docs. Please upload policy/product docs."
        tokens = len(text.split()) * 2

    return {
        "answer": text.strip(),
        "token_count": tokens,
        "cost_usd": _estimate_cost(tokens),
    }
