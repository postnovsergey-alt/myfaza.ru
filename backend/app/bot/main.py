"""Фабрика aiogram Bot + Dispatcher.

Модуль импортируется из webhook-эндпоинта. Bot и Dispatcher создаются
лениво (один экземпляр на процесс) и переиспользуются между запросами.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from functools import lru_cache
from typing import Any

from aiogram import BaseMiddleware, Bot, Dispatcher
from aiogram.types import TelegramObject
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config import get_settings
from app.db.base import get_sessionmaker


class DbSessionMiddleware(BaseMiddleware):
    """Открывает AsyncSession на каждый апдейт и коммитит в конце.

    Хендлеры получают её через параметр `db`. Ошибка в хендлере откатывает
    транзакцию — та же семантика, что у get_db в FastAPI.
    """

    def __init__(self, sessionmaker: async_sessionmaker[AsyncSession]) -> None:
        self._sessionmaker = sessionmaker

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        async with self._sessionmaker() as session:
            data["db"] = session
            try:
                result = await handler(event, data)
                await session.commit()
                return result
            except Exception:
                await session.rollback()
                raise


@lru_cache
def build_dispatcher() -> Dispatcher:
    """Единый Dispatcher на процесс.

    Импорт хендлеров — внутри, чтобы избежать циклической зависимости при
    сборе `app.bot` из тестов.
    """
    from app.bot.handlers import cycle_router, start_router

    dp = Dispatcher()
    dp.update.outer_middleware(DbSessionMiddleware(get_sessionmaker()))
    dp.include_router(start_router)
    dp.include_router(cycle_router)
    return dp


@lru_cache
def get_bot() -> Bot:
    token = get_settings().BOT_TOKEN
    if not token:
        raise RuntimeError("BOT_TOKEN пуст — Telegram-бот не сконфигурирован")
    return Bot(token=token)
