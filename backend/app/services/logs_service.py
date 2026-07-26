"""Дневные записи (daily_logs) — раздел 6.3, 8.4 ТЗ."""

from __future__ import annotations

from datetime import date
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.enums import FlowLevel, Mood
from app.db.models import DailyLog


async def list_logs(
    db: AsyncSession,
    user_id: UUID,
    *,
    from_date: date | None = None,
    to_date: date | None = None,
) -> list[DailyLog]:
    stmt = select(DailyLog).where(DailyLog.user_id == user_id).order_by(DailyLog.date.desc())
    if from_date is not None:
        stmt = stmt.where(DailyLog.date >= from_date)
    if to_date is not None:
        stmt = stmt.where(DailyLog.date <= to_date)
    result = await db.scalars(stmt)
    return list(result.all())


async def upsert_log(
    db: AsyncSession,
    user_id: UUID,
    on: date,
    *,
    flow: str | None,
    mood: str | None,
    symptoms: list[str] | None,
    note: str | None,
) -> DailyLog:
    log = await db.scalar(
        select(DailyLog).where(DailyLog.user_id == user_id, DailyLog.date == on)
    )
    if log is None:
        log = DailyLog(user_id=user_id, date=on)
        db.add(log)
    log.flow = FlowLevel(flow) if flow else None
    log.mood = Mood(mood) if mood else None
    log.symptoms = symptoms
    log.note = note
    await db.flush()
    # onupdate=func.now() пересчитывает updated_at на стороне БД —
    # без refresh() Pydantic попробует лениво подтянуть его в неподходящем месте
    await db.refresh(log)
    return log


async def delete_log(db: AsyncSession, user_id: UUID, on: date) -> bool:
    log = await db.scalar(
        select(DailyLog).where(DailyLog.user_id == user_id, DailyLog.date == on)
    )
    if log is None:
        return False
    await db.delete(log)
    return True
