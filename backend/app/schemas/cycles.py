"""DTO для /cycles, /logs, /predictions. Разделы 8.2–8.4 ТЗ."""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

# --------------------------------------------------------- cycles


class CycleIn(BaseModel):
    start_date: date
    end_date: date | None = None
    source: Literal["telegram", "web", "system"] = "web"


class CyclePatch(BaseModel):
    start_date: date | None = None
    end_date: date | None = None


class CycleEnd(BaseModel):
    end_date: date


class CycleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    start_date: date
    end_date: date | None
    cycle_length: int | None
    period_length: int | None
    is_predicted: bool
    is_anomaly: bool
    source: str
    created_at: datetime
    updated_at: datetime


# --------------------------------------------------------- logs


class DailyLogIn(BaseModel):
    flow: Literal["spotting", "light", "medium", "heavy"] | None = None
    mood: Literal["great", "good", "neutral", "low", "bad"] | None = None
    symptoms: list[str] | None = None
    note: str | None = Field(default=None, max_length=500)

    @field_validator("symptoms")
    @classmethod
    def _limit_symptoms(cls, v: list[str] | None) -> list[str] | None:
        if v is None:
            return v
        # Дедуп и мягкий предел — на случай, если фронт пришлёт кучу
        cleaned = sorted({s.strip().lower() for s in v if s and s.strip()})
        if len(cleaned) > 20:
            raise ValueError("Слишком много симптомов")
        return cleaned


class DailyLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    date: date
    flow: str | None
    mood: str | None
    symptoms: list[str] | None
    note: str | None
    created_at: datetime
    updated_at: datetime


# --------------------------------------------------------- predictions


class FertileWindow(BaseModel):
    start: date
    end: date


class PredictionOut(BaseModel):
    predicted_start: date
    predicted_end: date
    margin_days: int
    confidence: Literal["low", "medium", "high"]
    based_on_cycles: int
    ovulation_date: date
    fertile_window: FertileWindow
    current_cycle_day: int
    days_until_period: int
    is_overdue: bool
    overdue_days: int
    # true, если сейчас идёт менструация (открытый цикл, начался <=14 дней назад)
    is_period_active: bool = False


class CalendarDay(BaseModel):
    date: date
    state: Literal[
        "period_actual", "period_predicted", "fertile", "ovulation", "normal"
    ]
    has_log: bool
    is_today: bool = False
    cycle_day: int | None = None


class CalendarOut(BaseModel):
    month: str  # "YYYY-MM"
    days: list[CalendarDay]
