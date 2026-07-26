"""Подключение к БД: async engine, фабрика сессий, базовый класс моделей.

Engine создаётся лениво, при первом обращении. Это важно: импорт моделей
(в тестах, в Alembic, в линтерах) не должен требовать живой БД и драйвера.
"""
import os
import uuid
from collections.abc import AsyncGenerator
from datetime import datetime
from functools import lru_cache

from sqlalchemy import DateTime, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.pool import NullPool

from app.config import get_settings


class Base(DeclarativeBase):
    pass


class UUIDMixin:
    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


@lru_cache
def get_engine() -> AsyncEngine:
    settings = get_settings()
    # В тестах используем NullPool: pytest-asyncio создаёт новый event loop
    # на каждый тест, а asyncpg-соединения из пула привязаны к старому
    # loop и падают с "Event loop is closed" при попытке использовать.
    if os.getenv("PYTEST_CURRENT_TEST") or os.getenv("USE_NULL_POOL") == "1":
        return create_async_engine(settings.database_url, poolclass=NullPool)
    return create_async_engine(
        settings.database_url,
        echo=settings.APP_ENV == "local",
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
    )


@lru_cache
def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(get_engine(), expire_on_commit=False, class_=AsyncSession)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Зависимость FastAPI: сессия на запрос, коммит при успехе."""
    async with get_sessionmaker()() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
