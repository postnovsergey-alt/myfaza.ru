"""Обёртка вокруг чистого prediction.compute для работы с БД."""

from __future__ import annotations

import calendar
from datetime import UTC, date, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Cycle, DailyLog
from app.services import cycles_service
from app.services.prediction import PredictionInputs, PredictionResult, compute


class NoDataError(Exception):
    code = "NO_CYCLES"
    http_status = 404


def _today() -> date:
    return datetime.now(tz=UTC).date()


async def _fetch_recent_completed_lengths(
    db: AsyncSession, user_id: UUID, limit: int = 12
) -> list[int]:
    result = await db.scalars(
        select(Cycle.cycle_length)
        .where(Cycle.user_id == user_id, Cycle.cycle_length.is_not(None))
        .order_by(Cycle.start_date.desc())
        .limit(limit)
    )
    return [int(v) for v in result.all() if v is not None]


async def _last_cycle_start(db: AsyncSession, user_id: UUID) -> date | None:
    return await db.scalar(
        select(Cycle.start_date)
        .where(Cycle.user_id == user_id)
        .order_by(Cycle.start_date.desc())
    )


# Разумный потолок «менструация всё ещё идёт»: обычно 2–10 дней.
# Если цикл открытый, но начался больше двух недель назад — считаем, что
# пользователь просто забыл отметить окончание, и UI-кнопку не показываем.
_ACTIVE_PERIOD_MAX_DAYS = 14


async def is_period_active(
    db: AsyncSession, user_id: UUID, today: date | None = None
) -> bool:
    """True — если у пользователя есть открытый цикл (без end_date),
    начавшийся не более 14 дней назад."""
    today = today or _today()
    open_cycle_start = await db.scalar(
        select(Cycle.start_date)
        .where(Cycle.user_id == user_id, Cycle.end_date.is_(None))
        .order_by(Cycle.start_date.desc())
    )
    if open_cycle_start is None:
        return False
    days_since_start = (today - open_cycle_start).days
    return 0 <= days_since_start <= _ACTIVE_PERIOD_MAX_DAYS


async def predict_for_user(
    db: AsyncSession, user_id: UUID, today: date | None = None
) -> PredictionResult:
    last_start = await _last_cycle_start(db, user_id)
    if last_start is None:
        raise NoDataError("Ещё нет ни одного цикла")

    settings = await cycles_service.get_settings(db, user_id)
    lengths = await _fetch_recent_completed_lengths(db, user_id)

    inputs = PredictionInputs(
        completed_cycle_lengths=lengths,
        last_cycle_start=last_start,
        avg_cycle_length=settings.avg_cycle_length,
        avg_period_length=settings.avg_period_length,
        luteal_phase_length=settings.luteal_phase_length,
        today=today or _today(),
    )
    return compute(inputs)


# --------------------------------------------------------- календарь


def _iter_month(year: int, month: int):
    _, last = calendar.monthrange(year, month)
    for day in range(1, last + 1):
        yield date(year, month, day)


async def _all_cycles(db: AsyncSession, user_id: UUID) -> list[Cycle]:
    result = await db.scalars(
        select(Cycle).where(Cycle.user_id == user_id).order_by(Cycle.start_date.asc())
    )
    return list(result.all())


async def _log_dates(
    db: AsyncSession, user_id: UUID, month_start: date, month_end: date
) -> set[date]:
    result = await db.scalars(
        select(DailyLog.date).where(
            DailyLog.user_id == user_id,
            DailyLog.date >= month_start,
            DailyLog.date <= month_end,
        )
    )
    return set(result.all())


async def build_calendar(
    db: AsyncSession, user_id: UUID, year: int, month: int
) -> list[dict]:
    """Возвращает массив дней месяца с состоянием и флагом has_log."""
    month_start = date(year, month, 1)
    _, last_day = calendar.monthrange(year, month)
    month_end = date(year, month, last_day)

    cycles = await _all_cycles(db, user_id)
    log_dates = await _log_dates(db, user_id, month_start, month_end)

    # Прогноз следующего периода — если возможен
    prediction: PredictionResult | None = None
    try:
        prediction = await predict_for_user(db, user_id, today=_today())
    except NoDataError:
        prediction = None

    # Диапазон фактических менструаций
    actual_ranges: list[tuple[date, date]] = []
    for c in cycles:
        end = c.end_date or c.start_date
        actual_ranges.append((c.start_date, end))

    def in_range(d: date, ranges: list[tuple[date, date]]) -> bool:
        return any(a <= d <= b for a, b in ranges)

    today = _today()
    days = []
    for d in _iter_month(year, month):
        state: str = "normal"
        if in_range(d, actual_ranges):
            state = "period_actual"
        elif prediction is not None and (
            prediction.predicted_start <= d <= prediction.predicted_end
        ):
            state = "period_predicted"
        elif prediction is not None and d == prediction.ovulation_date:
            state = "ovulation"
        elif prediction is not None and (
            prediction.fertile_window_start <= d <= prediction.fertile_window_end
        ):
            state = "fertile"

        # Номер дня цикла — от последнего известного начала до текущей даты
        cycle_day: int | None = None
        for c in reversed(cycles):
            if c.start_date <= d:
                cycle_day = (d - c.start_date).days + 1
                break

        days.append(
            {
                "date": d,
                "state": state,
                "has_log": d in log_dates,
                "is_today": d == today,
                "cycle_day": cycle_day,
            }
        )
    return days
