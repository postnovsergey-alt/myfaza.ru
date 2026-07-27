"""Роутер /api/v1/predictions — раздел 8.3 ТЗ."""

from __future__ import annotations

import re

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.base import get_db
from app.db.models import User
from app.schemas.cycles import CalendarDay, CalendarOut, FertileWindow, PredictionOut
from app.services import predictions_service

router = APIRouter(prefix="/predictions", tags=["predictions"])

_MONTH_RE = re.compile(r"^(\d{4})-(\d{2})$")


@router.get("/next", response_model=PredictionOut)
async def next_prediction(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> PredictionOut:
    try:
        r = await predictions_service.predict_for_user(db, user.id)
    except predictions_service.NoDataError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": exc.code, "message": str(exc)}},
        ) from exc
    is_active = await predictions_service.is_period_active(db, user.id)
    return PredictionOut(
        predicted_start=r.predicted_start,
        predicted_end=r.predicted_end,
        margin_days=r.margin_days,
        confidence=r.confidence,
        based_on_cycles=r.based_on_cycles,
        ovulation_date=r.ovulation_date,
        fertile_window=FertileWindow(start=r.fertile_window_start, end=r.fertile_window_end),
        current_cycle_day=r.current_cycle_day,
        days_until_period=r.days_until_period,
        is_overdue=r.is_overdue,
        overdue_days=r.overdue_days,
        is_period_active=is_active,
    )


@router.get("/calendar", response_model=CalendarOut)
async def calendar_view(
    month: str = Query(pattern=r"^\d{4}-\d{2}$", examples=["2026-08"]),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> CalendarOut:
    m = _MONTH_RE.match(month)
    if not m:
        raise HTTPException(
            status_code=400,
            detail={"error": {"code": "BAD_MONTH", "message": "Ожидался формат YYYY-MM"}},
        )
    year, month_num = int(m.group(1)), int(m.group(2))
    if not 1 <= month_num <= 12:
        raise HTTPException(
            status_code=400,
            detail={"error": {"code": "BAD_MONTH", "message": "Месяц вне диапазона"}},
        )
    days = await predictions_service.build_calendar(db, user.id, year, month_num)
    return CalendarOut(
        month=month,
        days=[CalendarDay(**d) for d in days],
    )
