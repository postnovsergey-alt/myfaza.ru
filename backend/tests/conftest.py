import os

os.environ.setdefault("SECRET_KEY", "t" * 64)
os.environ.setdefault("FIELD_ENCRYPTION_KEY", "0123456789abcdef" * 4)
os.environ.setdefault("POSTGRES_PASSWORD", "test")
os.environ.setdefault("APP_ENV", "local")

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
