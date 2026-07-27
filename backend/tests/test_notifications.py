"""Тесты планировщика уведомлений — раздел 9.5 ТЗ (обязательные)."""

from __future__ import annotations

from datetime import UTC, date, datetime, time
from uuid import UUID
from zoneinfo import ZoneInfo

import pytest
from freezegun import freeze_time
from sqlalchemy import select

from app.db.base import get_sessionmaker
from app.db.enums import (
    Channel,
    NotificationStatus,
    NotificationType,
    NotifyChannel,
    Source,
)
from app.db.models import Cycle, Notification, User, UserSettings
from app.services import notifications as notif_service


async def _mk_user(
    *,
    tz: str = "Europe/Moscow",
    notify_time: time = time(10, 0),
    notify_channel: NotifyChannel = NotifyChannel.BOTH,
    telegram_id: int | None = 1001,
    before_days: int = 3,
) -> UUID:
    """Создаёт пользователя с настройками и одним активным циклом."""
    sm = get_sessionmaker()
    async with sm() as s:
        user = User(telegram_id=telegram_id, timezone=tz)
        s.add(user)
        await s.flush()
        s.add(
            UserSettings(
                user_id=user.id,
                notify_channel=notify_channel,
                notify_time=notify_time,
                notify_before_days=before_days,
            )
        )
        # Один цикл, начатый 4 дня назад — прогноз следующего через 24 дня
        # (avg_cycle_length=28), значит "period_upcoming" сработает
        # ровно за before_days дней до этого.
        s.add(
            Cycle(
                user_id=user.id,
                start_date=date(2026, 8, 1),
                end_date=date(2026, 8, 5),
                source=Source.SYSTEM,
            )
        )
        await s.commit()
        return user.id


async def _rows(user_id: UUID) -> list[Notification]:
    sm = get_sessionmaker()
    async with sm() as s:
        rs = await s.scalars(
            select(Notification).where(Notification.user_id == user_id)
        )
        return list(rs.all())


# ---------------------------------------------------------------- Vladivostok


@pytest.mark.asyncio
async def test_vladivostok_user_gets_notified_at_local_10am():
    """9.5 ТЗ: user в Asia/Vladivostok с notify_time=10:00 получает пуш
    в 10:00 по Владивостоку, а не по Москве."""
    user_id = await _mk_user(tz="Asia/Vladivostok", notify_time=time(10, 0))
    # 10:00 по Владивостоку 26 августа = 00:00 UTC того же дня
    vlad = ZoneInfo("Asia/Vladivostok")
    now = datetime(2026, 8, 26, 10, 0, tzinfo=vlad).astimezone(UTC)
    # 26 августа = 25 дней после начала цикла (2026-08-01), predicted 2026-08-29,
    # значит за 3 дня до — сработает period_upcoming именно сегодня.
    sm = get_sessionmaker()
    async with sm() as s:
        await notif_service.plan_notifications(s, now_utc=now)

    rows = await _rows(user_id)
    assert rows, "нет уведомлений на 10 утра владивостокского времени"
    kinds = {r.type for r in rows}
    assert NotificationType.PERIOD_UPCOMING in kinds


@pytest.mark.asyncio
async def test_vladivostok_user_ignored_at_moscow_10am():
    """Пользователь Владивостока не должен получать пуш в 10:00 по Москве —
    у него локально только 03:00 (не «час уведомления»)."""
    user_id = await _mk_user(tz="Asia/Vladivostok", notify_time=time(10, 0))
    msk = ZoneInfo("Europe/Moscow")
    now = datetime(2026, 8, 26, 10, 0, tzinfo=msk).astimezone(UTC)
    sm = get_sessionmaker()
    async with sm() as s:
        await notif_service.plan_notifications(s, now_utc=now)
    rows = await _rows(user_id)
    assert not rows, "не должно быть уведомлений вне часа"


# ---------------------------------------------------------------- дедупликация


@pytest.mark.asyncio
async def test_double_run_of_planner_creates_no_duplicates():
    """Двойной запуск plan_notifications в тот же час — одно уведомление
    на канал, а не два."""
    user_id = await _mk_user()
    msk = ZoneInfo("Europe/Moscow")
    now = datetime(2026, 8, 26, 10, 30, tzinfo=msk).astimezone(UTC)
    sm = get_sessionmaker()
    async with sm() as s:
        first = await notif_service.plan_notifications(s, now_utc=now)
    async with sm() as s:
        second = await notif_service.plan_notifications(s, now_utc=now)

    assert first, "первый запуск должен что-то вставить"
    assert second == [], "второй запуск не должен вставить ничего"

    rows = await _rows(user_id)
    # На оба канала — по одной записи, дубли не появились.
    per_channel: dict[Channel, int] = {}
    for r in rows:
        per_channel[r.channel] = per_channel.get(r.channel, 0) + 1
    for ch, cnt in per_channel.items():
        assert cnt == 1, f"по каналу {ch} ожидали 1, получили {cnt}"


# ---------------------------------------------------------------- channel=none


@pytest.mark.asyncio
async def test_channel_none_never_gets_notifications():
    """FR-4.6: notify_channel=none → ни одного уведомления."""
    user_id = await _mk_user(notify_channel=NotifyChannel.NONE)
    msk = ZoneInfo("Europe/Moscow")
    now = datetime(2026, 8, 26, 10, 0, tzinfo=msk).astimezone(UTC)
    sm = get_sessionmaker()
    async with sm() as s:
        await notif_service.plan_notifications(s, now_utc=now)
    assert await _rows(user_id) == []


# ---------------------------------------------------------------- unique constraint


@pytest.mark.asyncio
async def test_unique_constraint_blocks_manual_duplicates():
    """FR-4.8: UNIQUE(user_id, type, target_date, channel) — уровень БД."""
    from sqlalchemy.exc import IntegrityError

    user_id = await _mk_user()
    sm = get_sessionmaker()
    async with sm() as s:
        s.add(
            Notification(
                user_id=user_id,
                type=NotificationType.PERIOD_UPCOMING,
                target_date=date(2026, 8, 26),
                channel=Channel.WEB,
                status=NotificationStatus.PENDING,
            )
        )
        await s.commit()

    async with sm() as s:
        s.add(
            Notification(
                user_id=user_id,
                type=NotificationType.PERIOD_UPCOMING,
                target_date=date(2026, 8, 26),
                channel=Channel.WEB,
                status=NotificationStatus.PENDING,
            )
        )
        with pytest.raises(IntegrityError):
            await s.commit()


# ---------------------------------------------------------------- freeze_time


@pytest.mark.asyncio
async def test_freeze_time_plan_uses_frozen_now():
    """Планировщик должен слушаться freezegun при передаче now_utc=None."""
    user_id = await _mk_user()
    # 26 августа 10:00 MSK — сработает period_upcoming
    with freeze_time("2026-08-26 07:00:00"):  # 07:00 UTC = 10:00 MSK
        sm = get_sessionmaker()
        async with sm() as s:
            await notif_service.plan_notifications(s)
    rows = await _rows(user_id)
    assert rows, "freezegun не сработал"


# ---------------------------------------------------------------- log_reminder


@pytest.mark.asyncio
async def test_log_reminder_on_overdue():
    """Задержка 4-14 дней → log_reminder."""
    user_id = await _mk_user()
    # today - last_start = 4+28 = 32 → задержка (32 - 28) = 4 дня
    msk = ZoneInfo("Europe/Moscow")
    now = datetime(2026, 9, 2, 10, 0, tzinfo=msk).astimezone(UTC)
    sm = get_sessionmaker()
    async with sm() as s:
        await notif_service.plan_notifications(s, now_utc=now)
    kinds = {r.type for r in await _rows(user_id)}
    assert NotificationType.LOG_REMINDER in kinds
