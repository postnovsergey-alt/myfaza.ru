"""Валидация Telegram Mini App initData.

Раздел 10.1 ТЗ. Обязательные шаги:
1. HMAC-SHA256 подпись (проверяется aiogram);
2. auth_date не старше 24 часов — защита от replay-атак,
   этот шаг чаще всего пропускают.

Реализацию HMAC не пишем сами — используем aiogram.utils.web_app,
который применяется как справочная реализация.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from aiogram.utils.web_app import (
    WebAppInitData,
    safe_parse_webapp_init_data,
)

from app.config import get_settings


class InvalidInitDataError(Exception):
    code: str = "INVALID_INIT_DATA"


class InitDataExpiredError(InvalidInitDataError):
    code = "INIT_DATA_EXPIRED"


MAX_AGE = timedelta(hours=24)


def _now() -> datetime:
    return datetime.now(tz=UTC)


def parse_init_data(init_data: str, *, bot_token: str | None = None) -> WebAppInitData:
    """Проверяет HMAC-подпись и возраст initData, возвращает разобранные данные.

    bot_token можно передать явно (для тестов), по умолчанию — из настроек.
    """
    token = bot_token or get_settings().BOT_TOKEN
    if not token:
        raise InvalidInitDataError("BOT_TOKEN не сконфигурирован")

    try:
        parsed: WebAppInitData = safe_parse_webapp_init_data(token=token, init_data=init_data)
    except (ValueError, TypeError) as exc:  # aiogram кидает ValueError на плохой подписи
        raise InvalidInitDataError(str(exc)) from exc

    # auth_date — обязательное поле, проверка возраста (10.1 п.6 ТЗ)
    auth_dt = parsed.auth_date
    if auth_dt.tzinfo is None:
        auth_dt = auth_dt.replace(tzinfo=UTC)
    age = _now() - auth_dt
    if age > MAX_AGE:
        raise InitDataExpiredError(
            f"initData старше {MAX_AGE.total_seconds() / 3600:.0f} часов"
        )
    if age < -timedelta(minutes=5):
        # Значение из будущего — рассинхронизация часов или подделка
        raise InvalidInitDataError("auth_date в будущем")

    if parsed.user is None:
        raise InvalidInitDataError("initData не содержит поле user")

    return parsed


def extract_user(parsed: WebAppInitData) -> dict[str, Any]:
    """Возвращает подмножество полей user для сохранения в БД."""
    u = parsed.user
    assert u is not None, "parse_init_data гарантирует, что user не None"
    return {
        "telegram_id": u.id,
        "username": u.username,
        "first_name": u.first_name,
        "language_code": u.language_code,
    }
