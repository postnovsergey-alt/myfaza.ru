"""Криптография аутентификации.

- Пароли — argon2id (owasp-рекомендация, устойчив к GPU-атакам).
- JWT — HS256 на SECRET_KEY. Access короткоживущий, refresh — длинный
  и хранится в БД хешем (см. sessions, раздел 6.8 ТЗ).
- Одноразовые токены (email verify, link) — url-safe random.

Секретов в коде нет: всё из Settings, читается через get_settings().
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime, timedelta

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError

from app.config import get_settings

# argon2id с параметрами по умолчанию — они уже сбалансированы под ~50 ms
_hasher = PasswordHasher()

JWT_ALGORITHM = "HS256"


def hash_password(plain: str) -> str:
    """Возвращает argon2id-хеш. Длина хеша ≤ 255 (влезает в password_hash)."""
    return _hasher.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return _hasher.verify(hashed, plain)
    except (VerifyMismatchError, InvalidHashError):
        return False


def _now() -> datetime:
    return datetime.now(tz=UTC)


def create_access_token(user_id: str, extra: dict | None = None) -> tuple[str, int]:
    """Возвращает (JWT, ttl в секундах)."""
    settings = get_settings()
    ttl = timedelta(minutes=settings.JWT_ACCESS_TTL_MINUTES)
    now = _now()
    payload: dict = {
        "sub": str(user_id),
        "iat": int(now.timestamp()),
        "exp": int((now + ttl).timestamp()),
        "typ": "access",
    }
    if extra:
        payload.update(extra)
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm=JWT_ALGORITHM)
    return token, int(ttl.total_seconds())


def decode_access_token(token: str) -> dict:
    """Возвращает payload или бросает jwt.PyJWTError."""
    settings = get_settings()
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[JWT_ALGORITHM])


def generate_refresh_token() -> str:
    """Криптостойкий url-safe токен ~256 бит."""
    return secrets.token_urlsafe(48)


def hash_refresh_token(token: str) -> str:
    """SHA-256 hex для сравнения. В БД сам токен не хранится."""
    return hashlib.sha256(token.encode()).hexdigest()


def generate_link_token() -> str:
    """Одноразовый токен привязки аккаунтов (TTL 15 мин)."""
    return secrets.token_urlsafe(32)


def hash_ip(ip: str | None) -> str | None:
    """Хеш IP для sessions.ip_hash. Открытый IP не хранится (11.2 ТЗ)."""
    if not ip:
        return None
    settings = get_settings()
    return hashlib.sha256(f"{settings.SECRET_KEY}:{ip}".encode()).hexdigest()
