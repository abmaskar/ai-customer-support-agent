from __future__ import annotations

import logging
import time
import uuid
from typing import Any

from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_core.documents import Document as LCDocument
from langchain_text_splitters import RecursiveCharacterTextSplitter
from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

CHUNK_SIZE = 500
CHUNK_OVERLAP = 50


class RagService:
    """Qdrant-backed retrieval with graceful in-memory fallback."""

    def __init__(self) -> None:
        self._embeddings: HuggingFaceEmbeddings | None = None
        self._qdrant: QdrantClient | None = None
        self._fallback_chunks: list[dict[str, Any]] = []
        self._use_qdrant = False
        self._init_clients()

    def _init_clients(self) -> None:
        try:
            self._embeddings = HuggingFaceEmbeddings(model_name=settings.embedding_model)
            self._qdrant = QdrantClient(url=settings.qdrant_url)
            self._ensure_collection()
            self._use_qdrant = True
            logger.info("RAG: connected to Qdrant at %s", settings.qdrant_url)
        except Exception as exc:
            logger.warning("RAG: Qdrant unavailable (%s), using in-memory fallback", exc)
            self._use_qdrant = False

    def _ensure_collection(self) -> None:
        assert self._qdrant is not None
        assert self._embeddings is not None
        collections = [c.name for c in self._qdrant.get_collections().collections]
        if settings.qdrant_collection not in collections:
            dim = len(self._embeddings.embed_query("dimension probe"))
            self._qdrant.create_collection(
                collection_name=settings.qdrant_collection,
                vectors_config=qmodels.VectorParams(size=dim, distance=qmodels.Distance.COSINE),
            )

    def ingest_text(self, text: str, doc_id: str, filename: str) -> int:
        splitter = RecursiveCharacterTextSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)
        parts = splitter.split_text(text)
        if not parts:
            parts = [text]

        if self._use_qdrant and self._qdrant and self._embeddings:
            vectors = self._embeddings.embed_documents(parts)
            points = []
            for idx, (part, vec) in enumerate(zip(parts, vectors)):
                points.append(
                    qmodels.PointStruct(
                        id=str(uuid.uuid4()),
                        vector=vec,
                        payload={
                            "doc_id": doc_id,
                            "source": filename,
                            "content": part,
                            "chunk_index": idx,
                        },
                    )
                )
            self._qdrant.upsert(collection_name=settings.qdrant_collection, points=points)
            return len(parts)

        for idx, part in enumerate(parts):
            self._fallback_chunks.append(
                {"doc_id": doc_id, "source": filename, "content": part, "chunk_index": idx}
            )
        return len(parts)

    def search(self, query: str, top_k: int = 3) -> list[dict[str, Any]]:
        if self._use_qdrant and self._qdrant and self._embeddings:
            vector = self._embeddings.embed_query(query)
            hits = self._qdrant.search(
                collection_name=settings.qdrant_collection,
                query_vector=vector,
                limit=top_k,
            )
            return [
                {
                    "source": hit.payload.get("source", "unknown"),
                    "content": hit.payload.get("content", ""),
                    "score": float(hit.score),
                }
                for hit in hits
            ]

        # Keyword fallback
        q_tokens = {t for t in query.lower().split() if len(t) > 2}
        ranked: list[tuple[int, dict[str, Any]]] = []
        for chunk in self._fallback_chunks:
            overlap = len(q_tokens & {t for t in chunk["content"].lower().split() if len(t) > 2})
            if overlap:
                ranked.append((overlap, {**chunk, "score": overlap / max(len(q_tokens), 1)}))
        ranked.sort(key=lambda x: x[0], reverse=True)
        return [item[1] for item in ranked[:top_k]]


rag_service = RagService()
