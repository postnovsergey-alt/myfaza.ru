"""Логика личного кабинета — раздел FR-8 ТЗ."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import security
from app.db.models import PushSubscription, Session, User


class LastAuthMethodError(Exception):
    code = "LAST_AUTH_METHOD"
    http_status = 409


class InvalidCurrentPasswordError(Exception):
    code = "INVALID_CURRENT_PASSWORD"
    http_status = 400


def _now() -> datetime:
    return datetime.now(tz=UTC)


async def change_password(
    db: AsyncSession, user: User, *, current_password: str | None, new_password: str
) -> None:
    if user.password_hash is not None:
        if not current_password:
            raise InvalidCurrentPasswordError("Введите текущий пароль")
        if not security.verify_password(current_password, user.password_hash):
            raise InvalidCurrentPasswordError("Текущий пароль неверный")
    user.password_hash = security.hash_password(new_password)


async def set_or_change_email(db: AsyncSession, user: User, *, email: str) -> None:
    normalized = email.strip().lower()
    other = await db.scalar(
        select(User).where(User.email == normalized, User.id != user.id)
    )
    if other is not None:
        raise LastAuthMethodError("Email уже используется другим аккаунтом")
    user.email = normalized
    # В MVP считаем email подтверждённым сразу; отдельный /verify-эндпоинт
    # оставит окно на будущую двойную проверку.
    user.email_verified_at = _now()


async def unlink_telegram(db: AsyncSession, user: User) -> None:
    if user.email is None:
        raise LastAuthMethodError("Нельзя отвязать последний способ входа")
    user.telegram_id = None
    user.telegram_username = None


async def unlink_email(db: AsyncSession, user: User) -> None:
    if user.telegram_id is None:
        raise LastAuthMethodError("Нельзя отвязать последний способ входа")
    user.email = None
    user.email_verified_at = None
    user.password_hash = None


# --- Сессии --------------------------------------------------------------


async def list_sessions(db: AsyncSession, user_id: UUID) -> list[Session]:
    result = await db.scalars(
        select(Session)
        .where(Session.user_id == user_id, Session.revoked_at.is_(None))
        .order_by(Session.last_used_at.desc().nulls_last())
    )
    return list(result.all())


async def revoke_session(db: AsyncSession, user_id: UUID, session_id: UUID) -> bool:
    row = await db.get(Session, session_id)
    if row is None or row.user_id != user_id or row.revoked_at is not None:
        return False
    row.revoked_at = _now()
    return True


async def revoke_all_but(db: AsyncSession, user_id: UUID, keep_hash: str | None) -> int:
    stmt = update(Session).where(
        Session.user_id == user_id, Session.revoked_at.is_(None)
    )
    if keep_hash is not None:
        stmt = stmt.where(Session.refresh_token_hash != keep_hash)
    stmt = stmt.values(revoked_at=_now())
    result = await db.execute(stmt)
    return int(getattr(result, "rowcount", 0) or 0)


# --- Удаление аккаунта -----------------------------------------------------


async def hard_delete(db: AsyncSession, user_id: UUID) -> None:
    """Каскадное удаление. FR-7.2: hard delete, не soft.

    Каскад настроен на уровне FK (ondelete=CASCADE) — достаточно удалить
    самого пользователя. Push-подписки, сессии, циклы, логи, уведомления,
    настройки — уходят автоматически.
    """
    await db.execute(delete(User).where(User.id == user_id))


async def list_push_subscriptions(db: AsyncSession, user_id: UUID) -> list[PushSubscription]:
    result = await db.scalars(
        select(PushSubscription).where(
            PushSubscription.user_id == user_id,
            PushSubscription.is_active.is_(True),
        )
    )
    return list(result.all())
