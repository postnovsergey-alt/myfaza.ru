"""DTO для /auth. Раздел 8.1 ТЗ."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class TelegramAuthIn(BaseModel):
    init_data: str = Field(min_length=1)


class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    timezone: str = Field(default="Europe/Moscow", max_length=64)


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class RefreshIn(BaseModel):
    refresh_token: str = Field(min_length=1)


class LogoutIn(BaseModel):
    refresh_token: str = Field(min_length=1)


class ConsentIn(BaseModel):
    version: str = Field(min_length=1, max_length=16)


class LinkCreateIn(BaseModel):
    direction: str = Field(pattern="^(tg_to_web|web_to_tg)$", default="tg_to_web")


class LinkConfirmWebIn(BaseModel):
    token: str = Field(min_length=1, max_length=64)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str | None = None
    telegram_id: int | None = None
    telegram_username: str | None = None
    display_name: str | None = None
    locale: str
    timezone: str
    consent_given_at: datetime | None = None
    consent_version: str | None = None
    onboarding_completed: bool


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    expires_in: int
    token_type: str = "Bearer"
    user: UserOut


class LinkCreateOut(BaseModel):
    token: str
    link_url: str
    expires_at: datetime


class ConsentOut(BaseModel):
    consent_given_at: datetime
    consent_version: str


class SimpleOk(BaseModel):
    ok: bool = True
