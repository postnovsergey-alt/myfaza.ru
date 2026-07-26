"""Перечисления из раздела 6 ТЗ. Имена значений совпадают с ТЗ дословно."""
from enum import StrEnum


class FlowLevel(StrEnum):
    SPOTTING = "spotting"
    LIGHT = "light"
    MEDIUM = "medium"
    HEAVY = "heavy"


class Mood(StrEnum):
    GREAT = "great"
    GOOD = "good"
    NEUTRAL = "neutral"
    LOW = "low"
    BAD = "bad"


class Source(StrEnum):
    TELEGRAM = "telegram"
    WEB = "web"
    SYSTEM = "system"


class Channel(StrEnum):
    TELEGRAM = "telegram"
    WEB = "web"


class NotifyChannel(StrEnum):
    TELEGRAM = "telegram"
    WEB = "web"
    BOTH = "both"
    NONE = "none"


class NotificationType(StrEnum):
    PERIOD_UPCOMING = "period_upcoming"
    PERIOD_START = "period_start"
    PERIOD_END = "period_end"
    OVULATION = "ovulation"
    LOG_REMINDER = "log_reminder"


class NotificationStatus(StrEnum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    SKIPPED = "skipped"


class Theme(StrEnum):
    AUTO = "auto"
    LIGHT = "light"
    DARK = "dark"


class LinkDirection(StrEnum):
    TG_TO_WEB = "tg_to_web"
    WEB_TO_TG = "web_to_tg"


def pg_enum(enum_cls, name: str):
    """Postgres ENUM с метками = значениями, а не именами членов.

    Без values_callable SQLAlchemy создаёт тип с метками из ИМЁН членов
    ('PENDING'), а не из значений ('pending'). Тогда server_default,
    записанный значением, не совпадает с меткой типа и миграция падает.
    Значения меток должны совпадать с ТЗ дословно — они уходят в API.
    """
    from sqlalchemy import Enum as SAEnum

    return SAEnum(
        enum_cls,
        name=name,
        native_enum=True,
        values_callable=lambda e: [m.value for m in e],
    )
