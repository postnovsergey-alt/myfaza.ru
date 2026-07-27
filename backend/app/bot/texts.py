"""Тексты уведомлений и сообщений бота — раздел 9.4 ТЗ.

Два режима: `discreet` (по умолчанию, дефолт FR-4.7) и обычный.
Дискретный текст никогда не содержит слов «менструация», «цикл»,
чтобы читаться при взгляде через плечо (см. DESIGN-SPEC 1.1).
"""

from __future__ import annotations

from typing import Literal

NotificationType = Literal[
    "period_upcoming", "period_start", "period_end", "ovulation", "log_reminder"
]

# --- заголовки одинаковые в обоих режимах — «Моя фаза» ---
BRAND_TITLE = "Моя фаза"


DISCREET_BODY: dict[str, str] = {
    "period_upcoming": "Напоминание — загляните в приложение",
    "period_start":    "Пора отметить сегодняшний день",
    "period_end":      "Есть что отметить",
    "ovulation":       "Заметка на сегодня",
    "log_reminder":    "Есть что отметить",
}


def _human_date(iso: str) -> str:
    """«14 августа» из «2026-08-14» — без импорта locale в проде."""
    from datetime import date

    d = date.fromisoformat(iso)
    months = [
        "января", "февраля", "марта", "апреля", "мая", "июня",
        "июля", "августа", "сентября", "октября", "ноября", "декабря",
    ]
    return f"{d.day} {months[d.month - 1]}"


def full_body(kind: NotificationType, target_date: str, days_before: int | None = None) -> str:
    if kind == "period_upcoming":
        return f"Менструация ожидается через {days_before} дн. — {_human_date(target_date)}"
    if kind == "period_start":
        return "Сегодня ожидается начало менструации. Отметить?"
    if kind == "period_end":
        return "Менструация закончилась?"
    if kind == "ovulation":
        return "Сегодня расчётный день овуляции"
    if kind == "log_reminder":
        return "Не забудьте отметить начало"
    return BRAND_TITLE


def build(
    kind: NotificationType,
    *,
    target_date: str,
    discreet: bool,
    days_before: int | None = None,
) -> tuple[str, str]:
    """Возвращает (title, body)."""
    if discreet:
        return BRAND_TITLE, DISCREET_BODY[kind]
    return BRAND_TITLE, full_body(kind, target_date, days_before)
