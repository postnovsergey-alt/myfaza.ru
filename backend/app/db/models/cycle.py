"""cycles, daily_logs — разделы 6.2 и 6.3 ТЗ."""
import uuid
from datetime import date

from sqlalchemy import (
    ARRAY,
    Boolean,
    CheckConstraint,
    Date,
    ForeignKey,
    Index,
    Integer,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.crypto import EncryptedString
from app.db.base import Base, TimestampMixin, UUIDMixin
from app.db.enums import FlowLevel, Mood, Source, pg_enum


class Cycle(Base, UUIDMixin, TimestampMixin):
    """Один ряд = одна менструация и цикл, который она открывает."""

    __tablename__ = "cycles"
    __table_args__ = (
        UniqueConstraint("user_id", "start_date", name="uq_cycles_user_start"),
        Index("ix_cycles_user_start_desc", "user_id", "start_date"),
        CheckConstraint("end_date IS NULL OR end_date >= start_date", name="ck_cycles_dates"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date | None] = mapped_column(Date)

    # Заполняется при появлении следующего цикла
    cycle_length: Mapped[int | None] = mapped_column(Integer)
    period_length: Mapped[int | None] = mapped_column(Integer)

    is_predicted: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    is_anomaly: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    source: Mapped[Source] = mapped_column(
        pg_enum(Source, "source"), default=Source.WEB
    )

    user: Mapped["User"] = relationship(back_populates="cycles")  # noqa: F821


class DailyLog(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "daily_logs"
    __table_args__ = (
        UniqueConstraint("user_id", "date", name="uq_daily_logs_user_date"),
        Index("ix_daily_logs_user_date_desc", "user_id", "date"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    date: Mapped[date] = mapped_column(Date, nullable=False)

    flow: Mapped[FlowLevel | None] = mapped_column(
        pg_enum(FlowLevel, "flow_level")
    )
    mood: Mapped[Mood | None] = mapped_column(pg_enum(Mood, "mood"))
    symptoms: Mapped[list[str] | None] = mapped_column(ARRAY(Text))

    # Свободный текст шифруется на уровне приложения (раздел 11.2)
    note: Mapped[str | None] = mapped_column(EncryptedString(1024))
