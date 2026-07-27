import os

os.environ.setdefault("SECRET_KEY", "t" * 64)
os.environ.setdefault("FIELD_ENCRYPTION_KEY", "0123456789abcdef" * 4)
os.environ.setdefault("POSTGRES_PASSWORD", "test")
os.environ.setdefault("APP_ENV", "local")
# BOT_TOKEN в .env пустой (комментарий-плейсхолдер), но docker-compose
# передаёт его как хвост строки, поэтому setdefault не срабатывает —
# принудительно задаём валидный тестовый токен.
os.environ["BOT_TOKEN"] = "123456:TESTBOTTOKENFORFAKEUSE"
os.environ["WEBHOOK_SECRET"] = "test-webhook-secret-do-not-use-in-prod"
# NullPool в тестах: pytest-asyncio использует новый loop на тест,
# а asyncpg-соединения не переносятся между loop'ами.
os.environ.setdefault("USE_NULL_POOL", "1")

# Сброс кеша настроек — Settings мог уже загрузиться при импорте.
from app.config import get_settings  # noqa: E402

get_settings.cache_clear()

import pytest  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

from app.db.base import get_sessionmaker  # noqa: E402
from app.main import app  # noqa: E402

# Таблицы, которые тесты меняют. Чистим перед каждым тестом, чтобы данные
# из соседних тестов не подтекали через общую БД контейнера.
_TABLES = [
    "account_link_tokens",
    "sessions",
    "user_settings",
    "daily_logs",
    "cycles",
    "notifications",
    "push_subscriptions",
    "audit_log",
    "users",
]


@pytest.fixture(autouse=True)
async def _truncate_db():
    """Перед каждым тестом обнуляем состояние всех таблиц."""
    sm = get_sessionmaker()
    async with sm() as s:
        await s.execute(text(f"TRUNCATE {', '.join(_TABLES)} RESTART IDENTITY CASCADE"))
        await s.commit()
    yield


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
