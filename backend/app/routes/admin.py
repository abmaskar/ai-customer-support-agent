from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pypdf import PdfReader
from sqlalchemy.orm import Session

from app.auth import require_admin
from app.database import get_db
from app.models import Document, User
from app.rag import rag_service
from app.schemas import DocumentOut

router = APIRouter(prefix="/api/admin", tags=["admin"])


async def _extract_text(file: UploadFile, payload: bytes) -> str:
    if file.filename and file.filename.lower().endswith(".pdf"):
        from io import BytesIO

        reader = PdfReader(BytesIO(payload))
        return "\n".join(page.extract_text() or "" for page in reader.pages).strip()
    return payload.decode("utf-8", errors="ignore")


@router.post("/upload", response_model=DocumentOut)
async def upload_document(
    user: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
    file: UploadFile = File(...),
) -> DocumentOut:
    payload = await file.read()
    if not payload:
        raise HTTPException(status_code=400, detail="Empty file")
    text = await _extract_text(file, payload)
    if not text.strip():
        raise HTTPException(status_code=400, detail="No text extracted from file")

    doc_id = str(uuid.uuid4())
    chunks = rag_service.ingest_text(text, doc_id=doc_id, filename=file.filename or "uploaded.txt")
    record = Document(
        id=doc_id,
        filename=file.filename or "uploaded.txt",
        title=file.filename or "uploaded.txt",
        chunk_count=chunks,
        uploaded_by_id=user.id,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return DocumentOut(
        id=record.id,
        filename=record.filename,
        title=record.title,
        chunk_count=record.chunk_count,
        created_at=record.created_at.isoformat(),
    )


@router.get("/documents", response_model=list[DocumentOut])
def list_documents(
    _: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
) -> list[DocumentOut]:
    docs = db.query(Document).order_by(Document.created_at.desc()).all()
    return [
        DocumentOut(
            id=d.id,
            filename=d.filename,
            title=d.title,
            chunk_count=d.chunk_count,
            created_at=d.created_at.isoformat(),
        )
        for d in docs
    ]
