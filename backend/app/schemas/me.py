"""DTO для /me и /account (личный кабинет, раздел 8.5 ТЗ)."""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class AuthMethodTelegram(BaseModel):
    linked: bool
    username: str | None = None


class AuthMethodEmail(BaseModel):
    linked: bool
    address: str | None = None
    verified: bool = False


class AuthMethods(BaseModel):
    telegram: AuthMethodTelegram
    email: AuthMethodEmail
    password_set: bool


class ConsentInfo(BaseModel):
    given_at: datetime | None = None
    version: str | None = None


class CycleStatus(BaseModel):
    current_cycle_day: int | None = None
    days_until_period: int | None = None
    is_overdue: bool = False


class MeOut(BaseModel):
    id: UUID
    display_name: str | None
    timezone: str
    locale: str
    auth_methods: AuthMethods
    consent: ConsentInfo
    cycle_status: CycleStatus
    created_at: datetime


class MePatch(BaseModel):
    display_name: str | None = Field(default=None, max_length=64)
    timezone: str | None = Field(default=None, max_length=64)
    locale: str | None = Field(default=None, max_length=5)


class EmailChangeIn(BaseModel):
    email: EmailStr


class PasswordChangeIn(BaseModel):
    current_password: str | None = None
    new_password: str = Field(min_length=8, max_length=128)


class SessionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    channel: str
    device_label: str | None
    last_used_at: datetime | None
    created_at: datetime


class HistoryPage(BaseModel):
    items: list
    page: int
    per_page: int
    total: int


class CycleHistoryItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    start_date: date
    end_date: date | None
    cycle_length: int | None
    period_length: int | None
    is_anomaly: bool


class LogHistoryItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    date: date
    flow: str | None
    mood: str | None
    symptoms: list[str] | None
    has_note: bool


class ConsentTextOut(BaseModel):
    version: str
    given_at: datetime | None
    text: str


class DeleteAccountIn(BaseModel):
    confirm: Literal["DELETE"]


class StatsOut(BaseModel):
    avg_cycle_length: int | None
    avg_period_length: int | None
    sigma: float | None
    regularity: Literal["regular", "slightly_irregular", "irregular"] | None
    last_lengths: list[int]
    anomaly_hint: str | None  # мягкое предупреждение (FR-6.5)
