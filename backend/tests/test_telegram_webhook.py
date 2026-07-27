"""Тесты бота: webhook-эндпоинт, /start, /start link_<token>, callback-кнопки.

Bot заменён на AsyncMock — реальный HTTP к api.telegram.org не идёт.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

import pytest
from aiogram import Bot
from aiogram.client.session.base import BaseSession
from aiogram.methods import (
    AnswerCallbackQuery,
    SendMessage,
    TelegramMethod,
)
from aiogram.types import Chat, Message
from sqlalchemy import select

from app.db.base import get_sessionmaker
from app.db.enums import LinkDirection
from app.db.models import AccountLinkToken, Cycle, User

WEBHOOK_URL = "/api/v1/telegram/webhook"
GOOD_SECRET = "test-webhook-secret-do-not-use-in-prod"
HEADERS_OK = {"X-Telegram-Bot-Api-Secret-Token": GOOD_SECRET}


class RecordingSession(BaseSession):
    """Заменяет aiogram-сессию: вместо HTTP кладёт вызовы в список.

    Обязательно наследуемся от BaseSession — иначе Bot проверит тип и
    молча заменит на дефолтную AiohttpSession.
    """

    def __init__(self) -> None:
        super().__init__()
        self.calls: list[TelegramMethod] = []

    async def make_request(self, bot, method, timeout=None):  # noqa: ARG002
        self.calls.append(method)
        if isinstance(method, SendMessage):
            return Message.model_construct(
                message_id=len(self.calls),
                date=datetime.now(tz=UTC),
                chat=Chat(id=method.chat_id, type="private"),
                text=method.text,
            )
        return True

    async def stream_content(  # type: ignore[override]
        self, url, headers=None, timeout=30, chunk_size=65536, raise_for_status=True
    ):
        if False:  # pragma: no cover — async-generator, тесты не используют
            yield b""

    async def close(self) -> None:  # type: ignore[override]
        return None

    def send_calls(self) -> list[SendMessage]:
        return [m for m in self.calls if isinstance(m, SendMessage)]

    def answer_calls(self) -> list[AnswerCallbackQuery]:
        return [m for m in self.calls if isinstance(m, AnswerCallbackQuery)]


@pytest.fixture
def stub_bot(monkeypatch):
    """Подменяет `get_bot()` на Bot c RecordingSession.

    Dispatcher не пересоздаём между тестами — Router-объекты глобальные,
    повторный include_router кинет 'router already attached'. Один
    Dispatcher на процесс, как и в проде.
    """
    from app.api.v1 import telegram_webhook as webhook_module
    from app.bot import main as bot_main

    session = RecordingSession()
    bot = Bot(token="0:test-token-for-mock", session=session)  # type: ignore[arg-type]
    # Патчим и модуль-владелец функции, и модуль-потребитель — иначе
    # уже импортированное `from ... import get_bot` продолжает
    # указывать на оригинал.
    monkeypatch.setattr(bot_main, "get_bot", lambda: bot)
    monkeypatch.setattr(webhook_module, "get_bot", lambda: bot)
    # Прокидываем session как атрибут для удобства ассертов
    bot._recording = session  # type: ignore[attr-defined]
    return bot


def _msg_update(*, tg_id: int, text: str, username: str | None = None, update_id: int = 1) -> dict:
    ts = int(datetime.now(tz=UTC).timestamp())
    user = {"id": tg_id, "is_bot": False, "first_name": "Test"}
    if username:
        user["username"] = username
    return {
        "update_id": update_id,
        "message": {
            "message_id": update_id,
            "date": ts,
            "chat": {"id": tg_id, "type": "private", "first_name": "Test"},
            "from": user,
            "text": text,
        },
    }


def _callback_update(*, tg_id: int, data: str, update_id: int = 100) -> dict:
    ts = int(datetime.now(tz=UTC).timestamp())
    return {
        "update_id": update_id,
        "callback_query": {
            "id": f"cb{update_id}",
            "from": {"id": tg_id, "is_bot": False, "first_name": "Test"},
            "message": {
                "message_id": update_id,
                "date": ts,
                "chat": {"id": tg_id, "type": "private", "first_name": "Test"},
                "text": "Сегодня ожидается начало менструации. Отметить?",
            },
            "chat_instance": "test-chat-instance",
            "data": data,
        },
    }


# ---------- секрет ----------


async def test_webhook_rejects_missing_secret(client):
    r = await client.post(WEBHOOK_URL, json=_msg_update(tg_id=1, text="/start"))
    assert r.status_code == 401


async def test_webhook_rejects_wrong_secret(client):
    r = await client.post(
        WEBHOOK_URL,
        json=_msg_update(tg_id=1, text="/start"),
        headers={"X-Telegram-Bot-Api-Secret-Token": "wrong"},
    )
    assert r.status_code == 401


async def test_webhook_rejects_bad_json(client):
    r = await client.post(
        WEBHOOK_URL,
        content=b"{not json}",
        headers={**HEADERS_OK, "Content-Type": "application/json"},
    )
    assert r.status_code == 400


# ---------- /start ----------


async def test_start_creates_user_and_replies(client, stub_bot):
    r = await client.post(
        WEBHOOK_URL,
        json=_msg_update(tg_id=42, text="/start", username="tester"),
        headers=HEADERS_OK,
    )
    assert r.status_code == 200

    sm = get_sessionmaker()
    async with sm() as s:
        user = await s.scalar(select(User).where(User.telegram_id == 42))
    assert user is not None
    assert user.telegram_username == "tester"

    # Ответ пользователю ушёл через bot(SendMessage(...))
    sends = stub_bot._recording.send_calls()
    assert sends and sends[-1].chat_id == 42
    assert "приложение" in sends[-1].text.lower()


async def test_start_link_binds_telegram_to_existing_web_user(client, stub_bot):
    """Deep-link `/start link_<token>` привязывает TG-id к веб-аккаунту."""
    sm = get_sessionmaker()
    async with sm() as s:
        user = User(email="ann@example.com", password_hash="x")
        s.add(user)
        await s.flush()
        s.add(
            AccountLinkToken(
                token="ttoken12345",
                user_id=user.id,
                direction=LinkDirection.WEB_TO_TG,
                expires_at=datetime.now(tz=UTC) + timedelta(minutes=10),
            )
        )
        await s.commit()
        uid = user.id

    r = await client.post(
        WEBHOOK_URL,
        json=_msg_update(tg_id=77, text="/start link_ttoken12345", username="ann"),
        headers=HEADERS_OK,
    )
    assert r.status_code == 200

    async with sm() as s:
        refreshed = await s.get(User, uid)
    assert refreshed is not None
    assert refreshed.telegram_id == 77
    assert refreshed.telegram_username == "ann"


async def test_start_link_expired_token_reports_error(client, stub_bot):
    sm = get_sessionmaker()
    async with sm() as s:
        user = User(email="b@example.com", password_hash="x")
        s.add(user)
        await s.flush()
        s.add(
            AccountLinkToken(
                token="expired1",
                user_id=user.id,
                direction=LinkDirection.WEB_TO_TG,
                expires_at=datetime.now(tz=UTC) - timedelta(minutes=1),
            )
        )
        await s.commit()

    r = await client.post(
        WEBHOOK_URL,
        json=_msg_update(tg_id=88, text="/start link_expired1"),
        headers=HEADERS_OK,
    )
    assert r.status_code == 200

    text = stub_bot._recording.send_calls()[-1].text
    assert "истекла" in text or "использована" in text


# ---------- callback cyc:start:* ----------


async def _make_tg_user(tg_id: int) -> User:
    sm = get_sessionmaker()
    async with sm() as s:
        u = User(telegram_id=tg_id, telegram_username="cb-user")
        s.add(u)
        await s.commit()
        return u


async def test_callback_start_today_creates_cycle(client, stub_bot):
    await _make_tg_user(200)
    r = await client.post(
        WEBHOOK_URL,
        json=_callback_update(tg_id=200, data="cyc:start:today", update_id=201),
        headers=HEADERS_OK,
    )
    assert r.status_code == 200

    sm = get_sessionmaker()
    async with sm() as s:
        user = await s.scalar(select(User).where(User.telegram_id == 200))
        assert user is not None
        cycle = await s.scalar(select(Cycle).where(Cycle.user_id == user.id))
    assert cycle is not None
    assert cycle.start_date == datetime.now(tz=UTC).date()

    # callback подтверждён — answer_callback_query вызван
    assert len(stub_bot._recording.answer_calls()) >= 1


async def test_callback_start_yesterday_creates_cycle(client, stub_bot):
    await _make_tg_user(201)
    r = await client.post(
        WEBHOOK_URL,
        json=_callback_update(tg_id=201, data="cyc:start:yesterday", update_id=202),
        headers=HEADERS_OK,
    )
    assert r.status_code == 200

    sm = get_sessionmaker()
    async with sm() as s:
        user = await s.scalar(select(User).where(User.telegram_id == 201))
        cycle = await s.scalar(select(Cycle).where(Cycle.user_id == user.id))
    assert cycle is not None
    yesterday = datetime.now(tz=UTC).date() - timedelta(days=1)
    assert cycle.start_date == yesterday


async def test_callback_notyet_does_not_create_cycle(client, stub_bot):
    await _make_tg_user(202)
    r = await client.post(
        WEBHOOK_URL,
        json=_callback_update(tg_id=202, data="cyc:notyet", update_id=203),
        headers=HEADERS_OK,
    )
    assert r.status_code == 200

    sm = get_sessionmaker()
    async with sm() as s:
        user = await s.scalar(select(User).where(User.telegram_id == 202))
        cycle = await s.scalar(select(Cycle).where(Cycle.user_id == user.id))
    assert cycle is None


async def test_callback_start_from_unknown_user_reports_error(client, stub_bot):
    """Кто-то дошёл до кнопки без /start (сценарий крайне редкий, но защитимся)."""
    r = await client.post(
        WEBHOOK_URL,
        json=_callback_update(tg_id=999, data="cyc:start:today", update_id=209),
        headers=HEADERS_OK,
    )
    assert r.status_code == 200

    # answer_callback_query всё равно вызывается — иначе Telegram показывает spinner
    assert len(stub_bot._recording.answer_calls()) >= 1
    sm = get_sessionmaker()
    async with sm() as s:
        cycles = await s.scalars(select(Cycle))
        assert list(cycles.all()) == []


async def test_callback_start_overlap_reports_gentle_error(client, stub_bot):
    """Если пользователь уже отметил сегодня — не 500, а понятная реплика."""
    await _make_tg_user(203)
    sm = get_sessionmaker()
    async with sm() as s:
        user = await s.scalar(select(User).where(User.telegram_id == 203))
        assert user is not None
        s.add(Cycle(user_id=user.id, start_date=date.today()))
        await s.commit()

    r = await client.post(
        WEBHOOK_URL,
        json=_callback_update(tg_id=203, data="cyc:start:today", update_id=210),
        headers=HEADERS_OK,
    )
    assert r.status_code == 200
    assert len(stub_bot._recording.answer_calls()) >= 1
    # Второго цикла не появилось
    async with sm() as s:
        user = await s.scalar(select(User).where(User.telegram_id == 203))
        assert user is not None
        cycles = list((await s.scalars(select(Cycle).where(Cycle.user_id == user.id))).all())
        assert len(cycles) == 1
