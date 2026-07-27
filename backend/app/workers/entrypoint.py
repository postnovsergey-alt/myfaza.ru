"""Точка входа воркера: APScheduler крутит plan_notifications ежечасно,
затем отправляет то, что успешно материализовалось.

В MVP реализация синхронно-async'ная через один процесс, без ARQ —
нагрузка мала, отдельная очередь избыточна. При росте — вынесем в ARQ.
"""

from __future__ import annotations

import asyncio
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select

from app.core.logging import setup_logging
from app.db.base import get_sessionmaker
from app.db.enums import NotificationStatus
from app.db.models import Notification
from app.services import notification_sender, notifications

log = logging.getLogger("worker")


async def tick() -> None:
    sm = get_sessionmaker()
    async with sm() as session:
        await notifications.plan_notifications(session)

    # Отправляем всё pending
    async with sm() as session:
        pending = (
            await session.scalars(
                select(Notification).where(Notification.status == NotificationStatus.PENDING)
            )
        ).all()
        for notif in pending:
            try:
                await notification_sender.send_notification(session, notif)
            except Exception:  # noqa: BLE001
                log.exception("failed to send notification %s", notif.id)
        await session.commit()


async def main() -> None:
    setup_logging("INFO")
    sched = AsyncIOScheduler(timezone="UTC")
    # Тик каждые 5 минут — планировщик сам решает, надо ли что-то делать
    # (у большинства пользователей в это время «не их час»)
    sched.add_job(tick, "interval", minutes=5, id="plan_and_send")
    sched.start()
    log.info("worker started")
    try:
        while True:
            await asyncio.sleep(3600)
    finally:
        sched.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
