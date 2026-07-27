"""DTO для /settings, /push. Раздел 8.5, 8.6 ТЗ."""

from __future__ import annotations

from datetime import time
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class SettingsOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    avg_cycle_length: int
    avg_period_length: int
    luteal_phase_length: int
    notify_before_days: int
    notify_time: time
    notify_on_start_day: bool
    notify_period_end: bool
    notify_ovulation: bool
    notify_channel: str
    discreet_mode: bool
    theme: str


class SettingsPatch(BaseModel):
    avg_cycle_length: int | None = Field(default=None, ge=15, le=90)
    avg_period_length: int | None = Field(default=None, ge=1, le=14)
    luteal_phase_length: int | None = Field(default=None, ge=8, le=20)
    notify_before_days: int | None = Field(default=None, ge=1, le=7)
    notify_time: time | None = None
    notify_on_start_day: bool | None = None
    notify_period_end: bool | None = None
    notify_ovulation: bool | None = None
    notify_channel: Literal["telegram", "web", "both", "none"] | None = None
    discreet_mode: bool | None = None
    theme: Literal["auto", "light", "dark"] | None = None


class PushSubscribeIn(BaseModel):
    endpoint: str = Field(min_length=8)
    keys: dict[str, str]


class PushSubscriptionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    endpoint: str
    user_agent: str | None
    is_active: bool


class VapidKeyOut(BaseModel):
    public_key: str
