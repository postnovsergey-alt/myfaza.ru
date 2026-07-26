"""Конфигурация приложения. Все значения читаются из окружения (.env)."""
from functools import lru_cache
from typing import Literal

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # --- Приложение ---
    APP_ENV: Literal["local", "staging", "production"] = "local"
    APP_NAME: str = "Моя фаза"
    PUBLIC_DOMAIN: str = "localhost"
    SECRET_KEY: str = Field(min_length=32)
    FIELD_ENCRYPTION_KEY: str = Field(min_length=32)
    LOG_LEVEL: str = "INFO"

    # --- База данных ---
    POSTGRES_HOST: str = "postgres"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "myfaza"
    POSTGRES_USER: str = "myfaza"
    POSTGRES_PASSWORD: str

    # --- Redis ---
    REDIS_URL: str = "redis://redis:6379/0"

    # --- Telegram ---
    BOT_TOKEN: str = ""
    BOT_USERNAME: str = "moyafaza_bot"
    WEBHOOK_SECRET: str = ""

    # --- Web Push ---
    VAPID_PUBLIC_KEY: str = ""
    VAPID_PRIVATE_KEY: str = ""
    VAPID_SUBJECT: str = ""

    # --- JWT ---
    JWT_ACCESS_TTL_MINUTES: int = 30
    JWT_REFRESH_TTL_DAYS: int = 60

    # --- Мониторинг ---
    SENTRY_DSN: str = ""

    @computed_field  # type: ignore[prop-decorator]
    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def sync_database_url(self) -> str:
        """Для Alembic — он работает синхронно."""
        return (
            f"postgresql+psycopg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def webapp_url(self) -> str:
        return f"https://{self.PUBLIC_DOMAIN}/app"


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
