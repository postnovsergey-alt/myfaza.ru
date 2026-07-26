"""Сервисный слой для циклов и дневных записей.

FR-1.5: границы длины цикла [15, 90] и длительности менструации [1, 14].
Пересечение с уже закрытыми циклами — блокируется. Значения вне границ,
но без пересечения, сохраняются, но с флагом `is_anomaly=True` — реальность
бывает разной, и удобство трекинга важнее псевдомедицинских ограничений.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.enums import Source
from app.db.models import Cycle, User, UserSettings

MAX_BACKDATE_DAYS = 90


# ---------------------------------------------------------------- ошибки


class CycleValidationError(Exception):
    code: str = "CYCLE_INVALID"
    http_status: int = 400

    def __init__(self, message: str, code: str | None = None):
        super().__init__(message)
        self.message = message
        if code:
            self.code = code


# ---------------------------------------------------------------- вспомогательное


def _today() -> date:
    return datetime.now(tz=UTC).date()


def _is_anomaly(period_length: int | None, cycle_length: int | None) -> bool:
    """FR-1.5: границы. Возвращает True, если хотя бы одно значение вне нормы."""
    if period_length is not None and not 1 <= period_length <= 14:
        return True
    return cycle_length is not None and not 15 <= cycle_length <= 90


def _validate_dates(start: date, end: date | None) -> None:
    if start > _today():
        raise CycleValidationError("Дата начала в будущем", code="CYCLE_FUTURE")
    if start < _today() - timedelta(days=MAX_BACKDATE_DAYS):
        raise CycleValidationError(
            f"Дата начала старше {MAX_BACKDATE_DAYS} дней", code="CYCLE_TOO_OLD"
        )
    if end is not None:
        if end < start:
            raise CycleValidationError(
                "Дата окончания раньше даты начала", code="CYCLE_END_BEFORE_START"
            )
        if end > _today():
            raise CycleValidationError("Дата окончания в будущем", code="CYCLE_FUTURE")


async def _get_all_cycles(db: AsyncSession, user_id: UUID) -> list[Cycle]:
    result = await db.scalars(
        select(Cycle).where(Cycle.user_id == user_id).order_by(Cycle.start_date.desc())
    )
    return list(result.all())


async def get_settings(db: AsyncSession, user_id: UUID) -> UserSettings:
    row = await db.get(UserSettings, user_id)
    if row is None:
        # Гарантия из auth_service._ensure_settings — но подстрахуемся
        row = UserSettings(user_id=user_id)
        db.add(row)
        await db.flush()
    return row


# ---------------------------------------------------------------- CRUD


async def list_cycles(
    db: AsyncSession,
    user_id: UUID,
    *,
    from_date: date | None = None,
    to_date: date | None = None,
) -> list[Cycle]:
    stmt = select(Cycle).where(Cycle.user_id == user_id).order_by(Cycle.start_date.desc())
    if from_date is not None:
        stmt = stmt.where(Cycle.start_date >= from_date)
    if to_date is not None:
        stmt = stmt.where(Cycle.start_date <= to_date)
    result = await db.scalars(stmt)
    return list(result.all())


def _check_overlap(
    all_cycles: list[Cycle],
    start: date,
    end: date | None,
    exclude_id: UUID | None,
) -> None:
    """Пересечение с любой уже сохранённой записью — блокируем."""
    for c in all_cycles:
        if c.id == exclude_id:
            continue
        # Диапазон существующего: [c.start_date, c.end_date OR c.start_date]
        c_end = c.end_date or c.start_date
        new_end = end or start
        overlap = not (new_end < c.start_date or start > c_end)
        if overlap:
            raise CycleValidationError(
                f"Пересекается с циклом {c.start_date.isoformat()}",
                code="CYCLE_OVERLAP",
            )


def _recompute_period_length(cycle: Cycle) -> None:
    if cycle.end_date is not None:
        cycle.period_length = (cycle.end_date - cycle.start_date).days + 1
    else:
        cycle.period_length = None


async def _link_previous_cycle_length(
    db: AsyncSession, user_id: UUID, new_cycle: Cycle
) -> None:
    """При появлении нового цикла у предыдущего появляется cycle_length."""
    prev = await db.scalar(
        select(Cycle)
        .where(Cycle.user_id == user_id, Cycle.start_date < new_cycle.start_date)
        .order_by(Cycle.start_date.desc())
    )
    if prev is None:
        return
    prev.cycle_length = (new_cycle.start_date - prev.start_date).days
    prev.is_anomaly = _is_anomaly(prev.period_length, prev.cycle_length)


async def create_cycle(
    db: AsyncSession,
    user: User,
    *,
    start: date,
    end: date | None,
    source: Source,
) -> Cycle:
    _validate_dates(start, end)
    existing = await _get_all_cycles(db, user.id)
    _check_overlap(existing, start, end, exclude_id=None)

    cycle = Cycle(
        user_id=user.id,
        start_date=start,
        end_date=end,
        source=source,
        is_predicted=False,
    )
    _recompute_period_length(cycle)
    cycle.is_anomaly = _is_anomaly(cycle.period_length, None)
    db.add(cycle)
    await db.flush()

    await _link_previous_cycle_length(db, user.id, cycle)
    return cycle


async def get_cycle(db: AsyncSession, user_id: UUID, cycle_id: UUID) -> Cycle:
    cycle = await db.get(Cycle, cycle_id)
    if cycle is None or cycle.user_id != user_id:
        raise CycleValidationError("Цикл не найден", code="CYCLE_NOT_FOUND")
    return cycle


async def update_cycle(
    db: AsyncSession,
    user: User,
    cycle_id: UUID,
    *,
    start: date | None,
    end: date | None,
    end_provided: bool,
) -> Cycle:
    cycle = await get_cycle(db, user.id, cycle_id)
    new_start = start if start is not None else cycle.start_date
    new_end = end if end_provided else cycle.end_date
    _validate_dates(new_start, new_end)

    existing = await _get_all_cycles(db, user.id)
    _check_overlap(existing, new_start, new_end, exclude_id=cycle.id)

    cycle.start_date = new_start
    cycle.end_date = new_end
    _recompute_period_length(cycle)

    # Пересчитать cycle_length у предыдущего и у самого cycle
    prev = await db.scalar(
        select(Cycle)
        .where(Cycle.user_id == user.id, Cycle.start_date < cycle.start_date)
        .order_by(Cycle.start_date.desc())
    )
    if prev is not None:
        prev.cycle_length = (cycle.start_date - prev.start_date).days
        prev.is_anomaly = _is_anomaly(prev.period_length, prev.cycle_length)

    nxt = await db.scalar(
        select(Cycle)
        .where(Cycle.user_id == user.id, Cycle.start_date > cycle.start_date)
        .order_by(Cycle.start_date.asc())
    )
    cycle.cycle_length = (
        (nxt.start_date - cycle.start_date).days if nxt is not None else None
    )
    cycle.is_anomaly = _is_anomaly(cycle.period_length, cycle.cycle_length)
    await db.flush()
    await db.refresh(cycle)
    return cycle


async def delete_cycle(db: AsyncSession, user_id: UUID, cycle_id: UUID) -> None:
    cycle = await get_cycle(db, user_id, cycle_id)
    # После удаления у «предыдущего» может пропасть/поменяться cycle_length
    prev = await db.scalar(
        select(Cycle)
        .where(Cycle.user_id == user_id, Cycle.start_date < cycle.start_date)
        .order_by(Cycle.start_date.desc())
    )
    nxt = await db.scalar(
        select(Cycle)
        .where(Cycle.user_id == user_id, Cycle.start_date > cycle.start_date)
        .order_by(Cycle.start_date.asc())
    )
    if prev is not None:
        prev.cycle_length = (
            (nxt.start_date - prev.start_date).days if nxt is not None else None
        )
        prev.is_anomaly = _is_anomaly(prev.period_length, prev.cycle_length)
    await db.delete(cycle)


async def end_current_cycle(db: AsyncSession, user: User, end: date) -> Cycle:
    """Закрыть текущую менструацию (последний цикл без end_date)."""
    cycle = await db.scalar(
        select(Cycle)
        .where(Cycle.user_id == user.id, Cycle.end_date.is_(None))
        .order_by(Cycle.start_date.desc())
    )
    if cycle is None:
        raise CycleValidationError(
            "Нет открытой менструации", code="NO_OPEN_CYCLE"
        )
    _validate_dates(cycle.start_date, end)
    cycle.end_date = end
    _recompute_period_length(cycle)
    cycle.is_anomaly = _is_anomaly(cycle.period_length, cycle.cycle_length)
    await db.flush()
    await db.refresh(cycle)
    return cycle
