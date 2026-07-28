"""Оркестрация аутентификации: регистрация, вход, обновление, отзыв, привязка.

Раздел 8.1 ТЗ (эндпоинты) + раздел 10 (правила).

Ключевое поведение:
- refresh-токен ротируется при каждом обновлении, старый помечается
  revoked_at (раздел 10.2 ТЗ);
- повторное использование отозванного refresh-токена трактуется как
  кража: все сессии пользователя отзываются, пользователь должен войти
  заново.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core import security
from app.db.enums import Channel, LinkDirection
from app.db.models import AccountLinkToken, Session, User, UserSettings


class AuthError(Exception):
    """Базовая ошибка аутентификации."""

    code: str = "AUTH_ERROR"
    http_status: int = 400

    def __init__(self, message: str, code: str | None = None, http_status: int | None = None):
        super().__init__(message)
        self.message = message
        if code:
            self.code = code
        if http_status:
            self.http_status = http_status


class InvalidCredentialsError(AuthError):
    code = "INVALID_CREDENTIALS"
    http_status = 401


class InvalidRefreshTokenError(AuthError):
    code = "INVALID_REFRESH_TOKEN"
    http_status = 401


class EmailAlreadyUsedError(AuthError):
    code = "EMAIL_ALREADY_USED"
    http_status = 409


class LinkTokenInvalidError(AuthError):
    code = "LINK_TOKEN_INVALID"
    http_status = 400


@dataclass
class TokenPair:
    access_token: str
    refresh_token: str
    expires_in: int


def _now() -> datetime:
    return datetime.now(tz=UTC)


def _refresh_expiry(remember: bool = False) -> datetime:
    s = get_settings()
    days = s.JWT_REFRESH_TTL_DAYS_REMEMBER if remember else s.JWT_REFRESH_TTL_DAYS
    return _now() + timedelta(days=days)


async def _ensure_settings(db: AsyncSession, user: User) -> None:
    """Создаёт запись user_settings, если её ещё нет."""
    existing = await db.get(UserSettings, user.id)
    if existing is None:
        db.add(UserSettings(user_id=user.id))
        await db.flush()


async def _issue_tokens(
    db: AsyncSession,
    user: User,
    channel: Channel,
    device_label: str | None = None,
    ip: str | None = None,
    remember: bool = False,
) -> TokenPair:
    """Создать новую сессию и вернуть пару токенов.

    remember=True — расширенный TTL (JWT_REFRESH_TTL_DAYS_REMEMBER),
    для чекбокса «Оставаться в системе».
    """
    access, ttl = security.create_access_token(str(user.id))
    refresh = security.generate_refresh_token()
    session = Session(
        user_id=user.id,
        refresh_token_hash=security.hash_refresh_token(refresh),
        channel=channel,
        device_label=device_label,
        ip_hash=security.hash_ip(ip),
        expires_at=_refresh_expiry(remember),
        last_used_at=_now(),
    )
    db.add(session)
    await db.flush()
    return TokenPair(access_token=access, refresh_token=refresh, expires_in=ttl)


# --- Email / пароль ---------------------------------------------------------

async def register_email(
    db: AsyncSession,
    *,
    email: str,
    password: str,
    timezone_name: str = "Europe/Moscow",
    device_label: str | None = None,
    ip: str | None = None,
    remember: bool = False,
) -> tuple[User, TokenPair]:
    email_norm = email.strip().lower()
    existing = await db.scalar(select(User).where(User.email == email_norm))
    if existing is not None:
        raise EmailAlreadyUsedError("Email уже используется")

    user = User(
        email=email_norm,
        password_hash=security.hash_password(password),
        timezone=timezone_name,
    )
    db.add(user)
    await db.flush()
    await _ensure_settings(db, user)
    tokens = await _issue_tokens(
        db, user, Channel.WEB, device_label=device_label, ip=ip, remember=remember,
    )
    return user, tokens


async def login_email(
    db: AsyncSession,
    *,
    email: str,
    password: str,
    device_label: str | None = None,
    ip: str | None = None,
    remember: bool = False,
) -> tuple[User, TokenPair]:
    email_norm = email.strip().lower()
    user = await db.scalar(select(User).where(User.email == email_norm))
    if user is None or user.password_hash is None:
        raise InvalidCredentialsError("Неверный email или пароль")
    if not security.verify_password(password, user.password_hash):
        raise InvalidCredentialsError("Неверный email или пароль")
    tokens = await _issue_tokens(
        db, user, Channel.WEB, device_label=device_label, ip=ip, remember=remember,
    )
    return user, tokens


# --- Telegram ---------------------------------------------------------------

async def authenticate_telegram(
    db: AsyncSession,
    *,
    telegram_id: int,
    username: str | None,
    device_label: str | None = None,
    ip: str | None = None,
) -> tuple[User, TokenPair, bool]:
    """Возвращает (user, tokens, created)."""
    user = await db.scalar(select(User).where(User.telegram_id == telegram_id))
    created = False
    if user is None:
        user = User(telegram_id=telegram_id, telegram_username=username)
        db.add(user)
        await db.flush()
        created = True
    else:
        if username and user.telegram_username != username:
            user.telegram_username = username
    await _ensure_settings(db, user)
    # Telegram Mini App живёт на устройстве пользователя вместе с самим
    # мессенджером — держим сессию как «remember», чтобы не разлогинивать
    # при редких заходах.
    tokens = await _issue_tokens(
        db, user, Channel.TELEGRAM, device_label=device_label, ip=ip, remember=True,
    )
    return user, tokens, created


# --- Refresh / logout -------------------------------------------------------

async def refresh_tokens(
    db: AsyncSession,
    *,
    refresh_token: str,
    ip: str | None = None,
) -> tuple[User, TokenPair]:
    """Ротация refresh: старый помечаем revoked_at, выдаём новую пару.

    Если приходит уже отозванный токен — это признак кражи, отзываем
    все сессии пользователя (раздел 10.2 ТЗ).
    """
    token_hash = security.hash_refresh_token(refresh_token)
    session = await db.scalar(select(Session).where(Session.refresh_token_hash == token_hash))
    if session is None:
        raise InvalidRefreshTokenError("Токен неизвестен")

    now = _now()
    if session.revoked_at is not None:
        # Компрометация: кто-то предъявил уже отозванный refresh.
        # Отзыв фиксируем отдельным коммитом, чтобы выбрасываемое исключение
        # не откатило зачистку сессий (get_db делает rollback на Exception).
        await db.execute(
            update(Session)
            .where(Session.user_id == session.user_id, Session.revoked_at.is_(None))
            .values(revoked_at=now)
        )
        await db.commit()
        raise InvalidRefreshTokenError(
            "Refresh-токен был отозван — все сессии сброшены",
            code="REFRESH_REUSE_DETECTED",
        )
    if session.expires_at <= now:
        session.revoked_at = now
        raise InvalidRefreshTokenError("Refresh-токен истёк")

    user = await db.get(User, session.user_id)
    if user is None:
        raise InvalidRefreshTokenError("Пользователь не найден")

    # Помечаем старую сессию отозванной, создаём новую того же канала
    session.revoked_at = now
    session.last_used_at = now
    tokens = await _issue_tokens(db, user, session.channel, ip=ip)
    return user, tokens


async def logout(db: AsyncSession, *, refresh_token: str) -> bool:
    token_hash = security.hash_refresh_token(refresh_token)
    session = await db.scalar(select(Session).where(Session.refresh_token_hash == token_hash))
    if session is None or session.revoked_at is not None:
        return False
    session.revoked_at = _now()
    return True


# --- Согласие ---------------------------------------------------------------

async def record_consent(db: AsyncSession, *, user: User, version: str) -> None:
    user.consent_given_at = _now()
    user.consent_version = version


# --- Привязка аккаунтов ------------------------------------------------------

async def create_link_token(
    db: AsyncSession,
    *,
    user: User,
    direction: LinkDirection,
) -> tuple[str, datetime]:
    token = security.generate_link_token()
    expires_at = _now() + timedelta(minutes=15)
    db.add(
        AccountLinkToken(
            token=token, user_id=user.id, direction=direction, expires_at=expires_at
        )
    )
    await db.flush()
    return token, expires_at


async def _consume_link_token(db: AsyncSession, token: str) -> AccountLinkToken:
    row = await db.get(AccountLinkToken, token)
    now = _now()
    if row is None:
        raise LinkTokenInvalidError("Токен неизвестен")
    if row.used_at is not None:
        raise LinkTokenInvalidError("Токен уже использован", code="LINK_TOKEN_USED")
    if row.expires_at <= now:
        raise LinkTokenInvalidError("Токен истёк", code="LINK_TOKEN_EXPIRED")
    row.used_at = now
    return row


async def confirm_link_web(
    db: AsyncSession,
    *,
    token: str,
    email: str,
    password: str,
) -> User:
    """Привязка веб-доступа к аккаунту, созданному в Telegram."""
    row = await _consume_link_token(db, token)
    if row.direction != LinkDirection.TG_TO_WEB:
        raise LinkTokenInvalidError("Неверное направление привязки")

    user = await db.get(User, row.user_id)
    if user is None:
        raise LinkTokenInvalidError("Пользователь не найден")

    email_norm = email.strip().lower()
    other = await db.scalar(
        select(User).where(User.email == email_norm, User.id != user.id)
    )
    if other is not None:
        raise EmailAlreadyUsedError("Email уже используется другим аккаунтом")

    user.email = email_norm
    user.password_hash = security.hash_password(password)
    return user


async def confirm_link_telegram(
    db: AsyncSession,
    *,
    token: str,
    telegram_id: int,
    username: str | None,
) -> User:
    """Привязка Telegram-доступа к аккаунту, созданному на сайте."""
    row = await _consume_link_token(db, token)
    if row.direction != LinkDirection.WEB_TO_TG:
        raise LinkTokenInvalidError("Неверное направление привязки")

    user = await db.get(User, row.user_id)
    if user is None:
        raise LinkTokenInvalidError("Пользователь не найден")

    other = await db.scalar(
        select(User).where(User.telegram_id == telegram_id, User.id != user.id)
    )
    if other is not None:
        raise EmailAlreadyUsedError(
            "Этот Telegram уже привязан к другому аккаунту",
            code="TELEGRAM_ALREADY_USED",
        )

    user.telegram_id = telegram_id
    if username:
        user.telegram_username = username
    return user


# --- Хелпер для current_user -----------------------------------------------

async def get_user_by_id(db: AsyncSession, user_id: str | UUID) -> User | None:
    if isinstance(user_id, str):
        try:
            user_id = UUID(user_id)
        except ValueError:
            return None
    return await db.get(User, user_id)
