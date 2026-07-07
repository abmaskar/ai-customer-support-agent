from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.auth import hash_password
from app.config import get_settings
from app.database import Base, SessionLocal, engine
from app.models import User
from app.routes import admin, auth, chat, metrics

logging.basicConfig(level=logging.INFO)
settings = get_settings()

app = FastAPI(title=settings.app_name, version="2.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(chat.router)
app.include_router(metrics.router)


def _seed_admin(db: Session) -> None:
    if db.query(User).filter(User.email == "admin@support.local").first():
        return
    admin_user = User(
        email="admin@support.local",
        hashed_password=hash_password("admin123"),
        is_admin=True,
    )
    db.add(admin_user)
    db.commit()


@app.on_event("startup")
def startup() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        _seed_admin(db)
    finally:
        db.close()


@app.get("/health")
def health() -> dict:
    return {
        "ok": True,
        "app": settings.app_name,
        "provider": settings.default_provider,
        "qdrant": settings.qdrant_url,
    }
