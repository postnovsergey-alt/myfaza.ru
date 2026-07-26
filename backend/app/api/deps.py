"""Зависимости FastAPI: текущий пользователь, IP клиента."""

from __future__ import annotations

import jwt
from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import security
from app.db.base import get_db
from app.db.models import User
from app.services import auth_service


def client_ip(request: Request) -> str | None:
    """Клиентский IP. За Nginx смотрим X-Forwarded-For, иначе peer."""
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else None


def device_label(user_agent: str | None = Header(default=None)) -> str | None:
    if not user_agent:
        return None
    return user_agent[:128]


async def get_current_user(
    authorization: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
) -> User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": {"code": "MISSING_TOKEN", "message": "Bearer-токен обязателен"}},
        )
    token = authorization.split(" ", 1)[1].strip()
    try:
        payload = security.decode_access_token(token)
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": {"code": "TOKEN_EXPIRED", "message": "Access-токен истёк"}},
        ) from exc
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": {"code": "INVALID_TOKEN", "message": "Access-токен некорректен"}},
        ) from exc

    if payload.get("typ") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": {"code": "INVALID_TOKEN", "message": "Неверный тип токена"}},
        )
    user = await auth_service.get_user_by_id(db, payload.get("sub", ""))
    if user is None or user.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": {"code": "USER_NOT_FOUND", "message": "Пользователь не найден"}},
        )
    return user
