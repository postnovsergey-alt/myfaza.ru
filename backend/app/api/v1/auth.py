"""Роутер /api/v1/auth. Раздел 8.1 ТЗ."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import client_ip, device_label, get_current_user
from app.config import get_settings
from app.db.base import get_db
from app.db.enums import LinkDirection
from app.db.models import User
from app.schemas.auth import (
    ConsentIn,
    ConsentOut,
    LinkConfirmWebIn,
    LinkCreateIn,
    LinkCreateOut,
    LoginIn,
    LogoutIn,
    RefreshIn,
    RegisterIn,
    SimpleOk,
    TelegramAuthIn,
    TokenResponse,
    UserOut,
)
from app.services import auth_service, telegram_auth

router = APIRouter(prefix="/auth", tags=["auth"])


def _error(exc: auth_service.AuthError) -> HTTPException:
    return HTTPException(
        status_code=exc.http_status,
        detail={"error": {"code": exc.code, "message": exc.message}},
    )


def _token_response(user: User, tokens: auth_service.TokenPair) -> TokenResponse:
    return TokenResponse(
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        expires_in=tokens.expires_in,
        user=UserOut.model_validate(user),
    )


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    body: RegisterIn,
    db: AsyncSession = Depends(get_db),
    ip: str | None = Depends(client_ip),
    device: str | None = Depends(device_label),
) -> TokenResponse:
    try:
        user, tokens = await auth_service.register_email(
            db,
            email=body.email,
            password=body.password,
            timezone_name=body.timezone,
            device_label=device,
            ip=ip,
        )
    except auth_service.AuthError as exc:
        raise _error(exc) from exc
    return _token_response(user, tokens)


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginIn,
    db: AsyncSession = Depends(get_db),
    ip: str | None = Depends(client_ip),
    device: str | None = Depends(device_label),
) -> TokenResponse:
    try:
        user, tokens = await auth_service.login_email(
            db,
            email=body.email,
            password=body.password,
            device_label=device,
            ip=ip,
        )
    except auth_service.AuthError as exc:
        raise _error(exc) from exc
    return _token_response(user, tokens)


@router.post("/telegram", response_model=TokenResponse)
async def telegram_login(
    body: TelegramAuthIn,
    db: AsyncSession = Depends(get_db),
    ip: str | None = Depends(client_ip),
    device: str | None = Depends(device_label),
) -> TokenResponse:
    try:
        parsed = telegram_auth.parse_init_data(body.init_data)
    except telegram_auth.InitDataExpiredError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": {"code": exc.code, "message": str(exc)}},
        ) from exc
    except telegram_auth.InvalidInitDataError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": {"code": exc.code, "message": str(exc)}},
        ) from exc

    tg_user = parsed.user
    assert tg_user is not None  # parse_init_data гарантирует
    try:
        user, tokens, _created = await auth_service.authenticate_telegram(
            db,
            telegram_id=tg_user.id,
            username=tg_user.username,
            device_label=device,
            ip=ip,
        )
    except auth_service.AuthError as exc:
        raise _error(exc) from exc
    return _token_response(user, tokens)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    body: RefreshIn,
    db: AsyncSession = Depends(get_db),
    ip: str | None = Depends(client_ip),
) -> TokenResponse:
    try:
        user, tokens = await auth_service.refresh_tokens(
            db, refresh_token=body.refresh_token, ip=ip
        )
    except auth_service.AuthError as exc:
        raise _error(exc) from exc
    return _token_response(user, tokens)


@router.post("/logout", response_model=SimpleOk)
async def logout(body: LogoutIn, db: AsyncSession = Depends(get_db)) -> SimpleOk:
    await auth_service.logout(db, refresh_token=body.refresh_token)
    return SimpleOk()


@router.post("/consent", response_model=ConsentOut)
async def consent(
    body: ConsentIn,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ConsentOut:
    await auth_service.record_consent(db, user=user, version=body.version)
    await db.flush()
    return ConsentOut(
        consent_given_at=user.consent_given_at,  # type: ignore[arg-type]
        consent_version=user.consent_version,  # type: ignore[arg-type]
    )


# --- Привязка аккаунтов -----------------------------------------------------

@router.post("/link/create", response_model=LinkCreateOut)
async def link_create(
    body: LinkCreateIn,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> LinkCreateOut:
    settings = get_settings()
    direction = LinkDirection(body.direction)
    token, expires_at = await auth_service.create_link_token(
        db, user=user, direction=direction
    )
    if direction == LinkDirection.TG_TO_WEB:
        url = f"https://{settings.PUBLIC_DOMAIN}/link?token={token}"
    else:
        url = f"https://t.me/{settings.BOT_USERNAME}?start=link_{token}"
    return LinkCreateOut(token=token, link_url=url, expires_at=expires_at)


@router.post("/link/confirm", response_model=TokenResponse)
async def link_confirm(
    body: LinkConfirmWebIn,
    db: AsyncSession = Depends(get_db),
    ip: str | None = Depends(client_ip),
    device: str | None = Depends(device_label),
) -> TokenResponse:
    """Подтверждение привязки веба к TG-аккаунту.

    Обратное направление (web→tg) обрабатывается ботом в спринте, где
    появится сам бот. Сейчас доступна одна ветка — она же нужна во фронте.
    """
    try:
        user = await auth_service.confirm_link_web(
            db, token=body.token, email=body.email, password=body.password
        )
        from app.db.enums import Channel

        tokens = await auth_service._issue_tokens(  # noqa: SLF001
            db, user, Channel.WEB, device_label=device, ip=ip
        )
    except auth_service.AuthError as exc:
        raise _error(exc) from exc
    return _token_response(user, tokens)
