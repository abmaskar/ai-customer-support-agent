from __future__ import annotations

import re
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.auth import create_access_token, hash_password, require_user, verify_password
from app.database import get_db
from app.models import User
from app.schemas import LoginRequest, RegisterRequest, TokenResponse

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse)
def register(req: RegisterRequest, db: Annotated[Session, Depends(get_db)]) -> TokenResponse:
    if db.query(User).filter(User.email == req.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    user = User(email=req.email, hashed_password=hash_password(req.password), is_admin=req.is_admin)
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_access_token(user.id, user.email, user.is_admin)
    return TokenResponse(access_token=token, user_id=user.id, email=user.email, is_admin=user.is_admin)


@router.post("/login", response_model=TokenResponse)
def login(req: LoginRequest, db: Annotated[Session, Depends(get_db)]) -> TokenResponse:
    user = db.query(User).filter(User.email == req.email).first()
    if user is None or not verify_password(req.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token(user.id, user.email, user.is_admin)
    return TokenResponse(access_token=token, user_id=user.id, email=user.email, is_admin=user.is_admin)


@router.get("/me")
def me(user: Annotated[User, Depends(require_user)]) -> dict:
    return {"id": user.id, "email": user.email, "is_admin": user.is_admin}
