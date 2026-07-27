"""Отправка одного уведомления в нужный канал.

Разделено от планировщика, чтобы отдельно тестировать и обрабатывать
ошибки транспорта (раздел 9.2, 9.3 ТЗ).
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot import texts
from app.config import get_settings
from app.db.enums import Channel, NotificationStatus, NotifyChannel
from app.db.models import Notification, PushSubscription, User, UserSettings

log = logging.getLogger(__name__)


class SendResult:
    def __init__(self, sent: bool, error: str | None = None):
        self.sent = sent
        self.error = error


def _now() -> datetime:
    return datetime.now(tz=UTC)


async def send_notification(
    db: AsyncSession,
    notif: Notification,
    *,
    tg_send=None,  # инъекция для тестов; None → aiogram-бот
    web_push_send=None,  # инъекция для тестов; None → pywebpush
) -> SendResult:
    """Отправка одной записи notifications.

    Возвращает SendResult. Побочно обновляет статус и sent_at
    в notification-объекте.
    """
    user = await db.get(User, notif.user_id)
    if user is None or user.deleted_at is not None:
        notif.status = NotificationStatus.SKIPPED
        notif.error = "user removed"
        return SendResult(False, notif.error)

    settings = await db.get(UserSettings, notif.user_id)
    discreet = settings.discreet_mode if settings else True

    title, body = texts.build(
        notif.type.value,  # type: ignore[arg-type]
        target_date=notif.target_date.isoformat(),
        discreet=discreet,
        days_before=(settings.notify_before_days if settings else None),
    )

    try:
        if notif.channel == Channel.TELEGRAM:
            if user.telegram_id is None:
                notif.status = NotificationStatus.SKIPPED
                notif.error = "no telegram id"
                return SendResult(False, notif.error)
            await _send_telegram(user.telegram_id, title, body, notif.type.value, tg_send)
        else:  # WEB
            subs = await _active_subs(db, notif.user_id)
            if not subs:
                notif.status = NotificationStatus.SKIPPED
                notif.error = "no push subscriptions"
                return SendResult(False, notif.error)
            await _send_web(db, subs, title, body, web_push_send)
    except _TelegramBlockedError:
        # Пользователь заблокировал бота — переключаем канал на web
        if settings is not None:
            settings.notify_channel = (
                NotifyChannel.WEB
                if settings.notify_channel == NotifyChannel.TELEGRAM
                else NotifyChannel.NONE if settings.notify_channel == NotifyChannel.BOTH
                else settings.notify_channel
            )
        notif.status = NotificationStatus.FAILED
        notif.error = "telegram blocked"
        return SendResult(False, notif.error)
    except Exception as exc:  # noqa: BLE001
        notif.status = NotificationStatus.FAILED
        notif.error = str(exc)[:500]
        log.warning("notification %s failed: %s", notif.id, exc)
        return SendResult(False, notif.error)

    notif.status = NotificationStatus.SENT
    notif.sent_at = _now()
    return SendResult(True)


class _TelegramBlockedError(Exception):
    pass


def _keyboard_for(kind: str):
    """Кнопки под сообщением — только для тех типов, где ждём ответ."""
    from app.bot import keyboards

    if kind == "period_start":
        return keyboards.period_start_prompt()
    if kind == "period_end":
        return keyboards.period_end_prompt()
    return None


async def _send_telegram(chat_id: int, title: str, body: str, kind: str, injected) -> None:
    if injected is not None:
        return await injected(chat_id, title, body)

    # Ленивая инициализация — тесты не должны требовать boot-token
    from aiogram.exceptions import (
        TelegramForbiddenError,
        TelegramRetryAfter,
    )

    from app.bot.main import get_bot

    bot = get_bot()
    try:
        # title уходит в дискретный заголовок нативного пуша, в чат его
        # дублировать не нужно — брендинг очевиден.
        await bot.send_message(chat_id=chat_id, text=body, reply_markup=_keyboard_for(kind))
    except TelegramForbiddenError as exc:  # bot was blocked
        raise _TelegramBlockedError(str(exc)) from exc
    except TelegramRetryAfter as exc:
        # Уважаем retry_after — оставим статус pending, ретрай сделает воркер
        raise RuntimeError(f"rate limited, retry_after={exc.retry_after}") from exc


async def _active_subs(db: AsyncSession, user_id: UUID) -> list[PushSubscription]:
    result = await db.scalars(
        select(PushSubscription).where(
            PushSubscription.user_id == user_id,
            PushSubscription.is_active.is_(True),
        )
    )
    return list(result.all())


async def _send_web(
    db: AsyncSession,
    subs: list[PushSubscription],
    title: str,
    body: str,
    injected,
) -> None:
    payload = json.dumps({"title": title, "body": body})
    if injected is not None:
        for sub in subs:
            await injected(sub, payload)
        return

    from pywebpush import WebPushException, webpush  # type: ignore[import-not-found]

    settings = get_settings()
    for sub in subs:
        info = {"endpoint": sub.endpoint, "keys": {"p256dh": sub.p256dh, "auth": sub.auth}}
        try:
            webpush(
                subscription_info=info,
                data=payload,
                vapid_private_key=settings.VAPID_PRIVATE_KEY,
                vapid_claims={"sub": settings.VAPID_SUBJECT or "mailto:admin@myfaza.ru"},
            )
            sub.last_success_at = _now()
            sub.failure_count = 0
        except WebPushException as exc:
            code = exc.response.status_code if exc.response is not None else 0
            if code in (404, 410):
                sub.is_active = False
            else:
                sub.failure_count += 1
                if sub.failure_count >= 5:
                    sub.is_active = False
            # логируем, но не роняем всю рассылку — остальные подписки должны уйти
            log.info("web push failed for sub %s: %s", sub.id, code)
