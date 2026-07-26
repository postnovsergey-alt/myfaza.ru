"""Логирование.

КРИТИЧНО (раздел 11.2 ТЗ): в логи не должны попадать даты циклов,
симптомы и заметки. Логируем user_id и тип операции, не содержимое.
"""
import logging
import sys

SENSITIVE_FIELDS = {
    "note", "symptoms", "start_date", "end_date", "date",
    "flow", "mood", "password", "password_hash", "init_data",
    "refresh_token", "access_token",
}


def scrub(data: dict) -> dict:
    """Вырезает чувствительные поля. Использовать в Sentry before_send."""
    return {
        k: ("[REDACTED]" if k in SENSITIVE_FIELDS else v)
        for k, v in data.items()
    }


def sentry_before_send(event, hint):
    for section in ("request", "extra", "contexts"):
        payload = event.get(section)
        if isinstance(payload, dict):
            event[section] = scrub(payload)
    return event


def setup_logging(level: str = "INFO") -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
        stream=sys.stdout,
    )
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
