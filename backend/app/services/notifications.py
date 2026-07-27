"""Планировщик уведомлений и отправка. Раздел 9 ТЗ.

Планировщик запускается ежечасно джобой `plan_notifications`. Для каждого
пользователя, у которого локальное время сейчас попадает в
[notify_time, notify_time + 1h), считаем прогноз и материализуем строки
в `notifications`. Дедупликация обеспечивается UNIQUE-констрейнтом
`(user_id, type, target_date, channel)` — вставка идёт `ON CONFLICT DO
NOTHING`, поэтому двойной запуск планировщика не приводит к дублям
(FR-4.8).

Отправка — отдельная функция `send_notification`, применяется к
каждой строке со статусом `pending`.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from typing import cast
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.texts import NotificationType as NotifKind
from app.db.enums import Channel, NotificationStatus, NotificationType, NotifyChannel
from app.db.models import Cycle, Notification, User, UserSettings
from app.services import predictions_service


@dataclass
class PendingNotification:
    """Что нужно вставить в notifications перед постановкой в очередь."""

    user_id: UUID
    kind: NotifKind
    target_date: date
    channel: Channel


def _tz(name: str) -> ZoneInfo:
    try:
        return ZoneInfo(name)
    except ZoneInfoNotFoundError:
        return ZoneInfo("UTC")


def _local_now(now_utc: datetime, tz_name: str) -> datetime:
    return now_utc.astimezone(_tz(tz_name))


def _channels_for(user_channel: NotifyChannel) -> list[Channel]:
    if user_channel == NotifyChannel.NONE:
        return []
    if user_channel == NotifyChannel.TELEGRAM:
        return [Channel.TELEGRAM]
    if user_channel == NotifyChannel.WEB:
        return [Channel.WEB]
    return [Channel.TELEGRAM, Channel.WEB]


def _hour_matches(local: datetime, notify_time: time) -> bool:
    """Локальный час совпадает с настроенным часом уведомлений."""
    return local.hour == notify_time.hour


async def _last_cycle_start(db: AsyncSession, user_id: UUID) -> date | None:
    return await db.scalar(
        select(Cycle.start_date).where(Cycle.user_id == user_id).order_by(Cycle.start_date.desc())
    )


async def _current_open_cycle(db: AsyncSession, user_id: UUID) -> Cycle | None:
    return await db.scalar(
        select(Cycle)
        .where(Cycle.user_id == user_id, Cycle.end_date.is_(None))
        .order_by(Cycle.start_date.desc())
    )


async def _compute_kinds_for_today(
    db: AsyncSession,
    user: User,
    settings: UserSettings,
    today: date,
) -> list[NotifKind]:
    """Какие типы уведомлений положены пользователю сегодня."""
    kinds: list[NotifKind] = []
    try:
        pred = await predictions_service.predict_for_user(db, user.id, today=today)
    except predictions_service.NoDataError:
        return []

    # period_upcoming: за N дней до прогнозного начала
    if pred.predicted_start - today == timedelta(days=settings.notify_before_days):
        kinds.append("period_upcoming")

    # period_start: в день ожидания
    if pred.predicted_start == today and settings.notify_on_start_day:
        kinds.append("period_start")

    # period_end: на день после расчётного конца текущей менструации
    if settings.notify_period_end:
        open_cycle = await _current_open_cycle(db, user.id)
        if open_cycle is not None:
            expected_end = open_cycle.start_date + timedelta(days=settings.avg_period_length - 1)
            if today == expected_end + timedelta(days=1):
                kinds.append("period_end")

    # ovulation
    if settings.notify_ovulation and pred.ovulation_date == today:
        kinds.append("ovulation")

    # log_reminder — «пора отметить», если задержка 4..14 дней
    if 4 <= pred.overdue_days <= 14:
        kinds.append("log_reminder")

    return kinds


async def _insert_row(
    db: AsyncSession,
    user_id: UUID,
    kind: NotifKind,
    target_date: date,
    channel: Channel,
) -> bool:
    """Вставляет одну запись notifications с ON CONFLICT DO NOTHING.

    Возвращает True, если строка реально вставилась (значит уведомление
    новое и должно быть поставлено в очередь на отправку). False — если
    такая уже была (двойной запуск планировщика, ретрай), тогда пропускаем.
    """
    stmt = (
        pg_insert(Notification)
        .values(
            user_id=user_id,
            type=NotificationType(kind),
            target_date=target_date,
            channel=channel,
            status=NotificationStatus.PENDING,
        )
        .on_conflict_do_nothing(
            index_elements=["user_id", "type", "target_date", "channel"],
        )
        .returning(Notification.id)
    )
    row = (await db.execute(stmt)).first()
    return row is not None


async def plan_notifications(
    db: AsyncSession, now_utc: datetime | None = None
) -> list[PendingNotification]:
    """Материализует уведомления на текущее часовое окно.

    Возвращает список реально вставленных pending-строк (для последующей
    отправки). Существующие пропускает — за это отвечает UNIQUE-констрейнт.
    """
    now = now_utc or datetime.now(tz=UTC)
    # Все не удалённые пользователи с настройками
    users = (
        await db.execute(
            select(User, UserSettings).join(
                UserSettings, UserSettings.user_id == User.id, isouter=False
            )
        )
    ).all()

    inserted: list[PendingNotification] = []
    for user, settings in users:
        user = cast(User, user)
        settings = cast(UserSettings, settings)
        if user.deleted_at is not None:
            continue
        channels = _channels_for(settings.notify_channel)
        if not channels:
            continue
        local = _local_now(now, user.timezone)
        if not _hour_matches(local, settings.notify_time):
            continue
        today = local.date()

        kinds = await _compute_kinds_for_today(db, user, settings, today)
        for kind in kinds:
            for ch in channels:
                target = _target_date_for(kind, today)
                if await _insert_row(db, user.id, kind, target, ch):
                    inserted.append(
                        PendingNotification(
                            user_id=user.id, kind=kind, target_date=target, channel=ch
                        )
                    )
    await db.commit()
    return inserted


def _target_date_for(kind: NotifKind, today: date) -> date:
    """Дата, к которой относится уведомление. Для сегодняшних — today.
    Для period_upcoming — тоже today, чтобы дедупликация работала per-день.
    """
    return today
