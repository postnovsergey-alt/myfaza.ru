"""users, user_settings — разделы 6.1 и 6.4 ТЗ."""
from __future__ import annotations

import uuid
from datetime import datetime, time
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Time,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin
from app.db.enums import NotifyChannel, Theme, pg_enum

if TYPE_CHECKING:
    from app.db.models.cycle import Cycle


class User(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(
            "telegram_id IS NOT NULL OR email IS NOT NULL",
            name="ck_users_has_auth_method",
        ),
    )

    telegram_id: Mapped[int | None] = mapped_column(BigInteger, unique=True, index=True)
    telegram_username: Mapped[str | None] = mapped_column(String(64))
    email: Mapped[str | None] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str | None] = mapped_column(String(255))
    email_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    display_name: Mapped[str | None] = mapped_column(String(64))

    locale: Mapped[str] = mapped_column(String(5), default="ru", server_default="ru")
    timezone: Mapped[str] = mapped_column(
        String(64), default="Europe/Moscow", server_default="Europe/Moscow"
    )

    consent_given_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    consent_version: Mapped[str | None] = mapped_column(String(16))
    onboarding_completed: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false"
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    settings: Mapped[UserSettings] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    cycles: Mapped[list[Cycle]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class UserSettings(Base, TimestampMixin):
    __tablename__ = "user_settings"

    user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )

    # Параметры цикла
    avg_cycle_length: Mapped[int] = mapped_column(Integer, default=28, server_default="28")
    avg_period_length: Mapped[int] = mapped_column(Integer, default=5, server_default="5")
    luteal_phase_length: Mapped[int] = mapped_column(Integer, default=14, server_default="14")

    # Уведомления. notify_before_days=3 — ключевое требование заказчика (FR-4.1)
    notify_before_days: Mapped[int] = mapped_column(Integer, default=3, server_default="3")
    notify_time: Mapped[time] = mapped_column(Time, default=time(10, 0), server_default="10:00")
    notify_on_start_day: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    notify_period_end: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    notify_ovulation: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    notify_channel: Mapped[NotifyChannel] = mapped_column(
        pg_enum(NotifyChannel, "notify_channel"),
        default=NotifyChannel.BOTH,
        server_default=NotifyChannel.BOTH.value,
    )

    # Дискретный режим включён по умолчанию (FR-4.7)
    discreet_mode: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    theme: Mapped[Theme] = mapped_column(
        pg_enum(Theme, "theme"),
        default=Theme.AUTO,
        server_default=Theme.AUTO.value,
    )

    user: Mapped[User] = relationship(back_populates="settings")
