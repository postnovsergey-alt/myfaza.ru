"""push_subscriptions, notifications — разделы 6.5 и 6.6 ТЗ."""
import uuid
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDMixin
from app.db.enums import Channel, NotificationStatus, NotificationType, pg_enum


class PushSubscription(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "push_subscriptions"

    user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    endpoint: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    p256dh: Mapped[str] = mapped_column(Text, nullable=False)
    auth: Mapped[str] = mapped_column(Text, nullable=False)
    user_agent: Mapped[str | None] = mapped_column(String(255))

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    failure_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")


class Notification(Base, UUIDMixin, TimestampMixin):
    """Журнал уведомлений.

    Уникальный ключ (user_id, type, target_date, channel) — механизм
    дедупликации из FR-4.8. Именно БД, а не память воркера, решает,
    отправляли ли мы это уведомление. Рестарт воркера или дубль в
    очереди не приведут ко второй отправке.
    """

    __tablename__ = "notifications"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "type", "target_date", "channel", name="uq_notifications_dedup"
        ),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    type: Mapped[NotificationType] = mapped_column(
        pg_enum(NotificationType, "notification_type"), nullable=False
    )
    target_date: Mapped[date] = mapped_column(Date, nullable=False)
    channel: Mapped[Channel] = mapped_column(
        pg_enum(Channel, "channel"), nullable=False
    )
    status: Mapped[NotificationStatus] = mapped_column(
        pg_enum(NotificationStatus, "notification_status"),
        default=NotificationStatus.PENDING,
        server_default=NotificationStatus.PENDING.value,
    )
    error: Mapped[str | None] = mapped_column(Text)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
