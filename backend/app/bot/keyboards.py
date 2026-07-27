"""Inline-клавиатуры бота — раздел 9.2 ТЗ.

Callback-данные короткие: у Telegram лимит 64 байта, плюс легче читать
логи. `cyc:start:today` — не `cycle_mark_start_today`.
"""

from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo

from app.config import get_settings


def open_app_button() -> InlineKeyboardMarkup:
    """Одна кнопка «Открыть приложение» — веб-версия под тем же доменом."""
    settings = get_settings()
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Открыть приложение",
                    web_app=WebAppInfo(url=settings.webapp_url),
                )
            ]
        ]
    )


def period_start_prompt() -> InlineKeyboardMarkup:
    """Кнопки под пушем period_start (ТЗ 9.2)."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Началось сегодня", callback_data="cyc:start:today"),
                InlineKeyboardButton(text="Началось вчера", callback_data="cyc:start:yesterday"),
            ],
            [
                InlineKeyboardButton(text="Ещё нет", callback_data="cyc:notyet"),
                InlineKeyboardButton(
                    text="Открыть приложение",
                    web_app=WebAppInfo(url=get_settings().webapp_url),
                ),
            ],
        ]
    )


def period_end_prompt() -> InlineKeyboardMarkup:
    """Кнопки под пушем period_end (ТЗ 3.5)."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Да, вчера", callback_data="cyc:end:yesterday"),
                InlineKeyboardButton(text="Да, сегодня", callback_data="cyc:end:today"),
            ],
            [InlineKeyboardButton(text="Ещё идёт", callback_data="cyc:end:notyet")],
        ]
    )
