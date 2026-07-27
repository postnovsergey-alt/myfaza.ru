"""Роутер /api/v1/push — раздел 8.6 ТЗ.

Управление подписками на Web Push.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.config import get_settings
from app.db.base import get_db
from app.db.enums import Channel, NotificationStatus, NotificationType
from app.db.models import Notification, PushSubscription, User
from app.schemas.settings import PushSubscribeIn, VapidKeyOut
from app.services import notification_sender

router = APIRouter(prefix="/push", tags=["push"])


@router.get("/vapid-key", response_model=VapidKeyOut)
async def vapid_key() -> VapidKeyOut:
    key = get_settings().VAPID_PUBLIC_KEY
    if not key:
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "code": "VAPID_NOT_CONFIGURED",
                    "message": "VAPID-ключ не сконфигурирован",
                }
            },
        )
    return VapidKeyOut(public_key=key)


@router.post("/subscribe", status_code=status.HTTP_201_CREATED)
async def subscribe(
    body: PushSubscribeIn,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    p256dh = body.keys.get("p256dh")
    auth = body.keys.get("auth")
    if not p256dh or not auth:
        raise HTTPException(
            status_code=400,
            detail={
                "error": {
                    "code": "BAD_KEYS",
                    "message": "keys.p256dh и keys.auth обязательны",
                }
            },
        )
    ua = request.headers.get("user-agent")
    # Уникальность — по endpoint. Если такая уже есть — не создаём вторую.
    existing = await db.scalar(
        select(PushSubscription).where(PushSubscription.endpoint == body.endpoint)
    )
    if existing is not None:
        existing.user_id = user.id  # переприкрепим устройство к текущему аккаунту
        existing.p256dh = p256dh
        existing.auth = auth
        existing.user_agent = ua[:255] if ua else None
        existing.is_active = True
        existing.failure_count = 0
        await db.flush()
        return {"id": str(existing.id)}
    sub = PushSubscription(
        user_id=user.id,
        endpoint=body.endpoint,
        p256dh=p256dh,
        auth=auth,
        user_agent=ua[:255] if ua else None,
    )
    db.add(sub)
    await db.flush()
    return {"id": str(sub.id)}


@router.post("/unsubscribe", status_code=status.HTTP_204_NO_CONTENT)
async def unsubscribe(
    body: dict,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    endpoint = body.get("endpoint")
    if not endpoint:
        raise HTTPException(
            status_code=400,
            detail={"error": {"code": "BAD_INPUT", "message": "endpoint обязателен"}},
        )
    sub = await db.scalar(
        select(PushSubscription).where(
            PushSubscription.endpoint == endpoint,
            PushSubscription.user_id == user.id,
        )
    )
    if sub is not None:
        await db.delete(sub)


@router.post("/test")
async def test_push(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """Тестовое уведомление во все активные каналы пользователя.
    Rate limit: 1/мин на пользователя, чтобы не заваливать себя случайно.
    """
    await _rate_limit_test(user.id)
    subs = await db.scalars(
        select(PushSubscription).where(
            PushSubscription.user_id == user.id, PushSubscription.is_active.is_(True)
        )
    )
    subs_list = list(subs.all())

    sent_web = 0
    sent_tg = 0
    if subs_list:
        # Пишем pending-запись и сразу шлём
        notif = Notification(
            user_id=user.id,
            type=NotificationType.LOG_REMINDER,
            target_date=datetime.now(tz=UTC).date(),
            channel=Channel.WEB,
            status=NotificationStatus.PENDING,
        )
        db.add(notif)
        await db.flush()
        result = await notification_sender.send_notification(db, notif)
        if result.sent:
            sent_web = len(subs_list)
    if user.telegram_id is not None:
        notif = Notification(
            user_id=user.id,
            type=NotificationType.LOG_REMINDER,
            target_date=datetime.now(tz=UTC).date(),
            channel=Channel.TELEGRAM,
            status=NotificationStatus.PENDING,
        )
        db.add(notif)
        await db.flush()
        result = await notification_sender.send_notification(db, notif)
        if result.sent:
            sent_tg = 1
    return {"sent_web": sent_web, "sent_telegram": sent_tg}


# --- rate limit через Redis --------------------------------------------------

_LIMIT_WINDOW = timedelta(minutes=1)


async def _rate_limit_test(user_id) -> None:
    """1 запрос в минуту на пользователя. Если Redis недоступен —
    ограничение отключается (лучше не блокировать функциональность
    из-за инфраструктурной ошибки в мониторинге)."""
    try:
        from redis.asyncio import from_url

        client = from_url(get_settings().REDIS_URL)
        key = "rl:pushtest:" + hashlib.sha256(str(user_id).encode()).hexdigest()[:16]
        # SET NX EX
        ok = await client.set(key, "1", ex=int(_LIMIT_WINDOW.total_seconds()), nx=True)
        await client.aclose()
        if not ok:
            raise HTTPException(
                status_code=429,
                detail={
                    "error": {
                        "code": "PUSH_TEST_RATE_LIMIT",
                        "message": "Не чаще одного тестового пуша в минуту",
                    }
                },
            )
    except HTTPException:
        raise
    except Exception:
        # Redis не отвечает — пропускаем без лимита
        return
