"""Роутеры aiogram — подключаются в app.bot.main.build_dispatcher."""

from app.bot.handlers.cycle import router as cycle_router
from app.bot.handlers.start import router as start_router

__all__ = ["start_router", "cycle_router"]
