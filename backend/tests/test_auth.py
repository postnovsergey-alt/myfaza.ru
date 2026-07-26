"""Тесты аутентификации — раздел 8.1 и 10 ТЗ.

Покрывают все обязательные сценарии из промпта спринта 2:
- initData: валидный / протухший / битый hash / отсутствующий user
- регистрация и вход по email + argon2id
- refresh: ротация, кража отозванного, истёкший, logout
- link-токен: одноразовость, TTL, неверное направление
"""

from __future__ import annotations

import time
from datetime import UTC, timedelta

from freezegun import freeze_time

from tests.telegram_helpers import build_init_data

BOT_TOKEN = "123456:TESTBOTTOKENFORFAKEUSE"


# ---------------------------------------------------------------- email/pw


async def test_register_returns_tokens_and_user(client):
    r = await client.post(
        "/api/v1/auth/register",
        json={"email": "a@example.com", "password": "correct-horse-battery"},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["token_type"] == "Bearer"
    assert body["access_token"]
    assert body["refresh_token"]
    assert body["expires_in"] > 0
    assert body["user"]["email"] == "a@example.com"
    assert body["user"]["consent_given_at"] is None


async def test_register_duplicate_email_conflict(client):
    payload = {"email": "dup@example.com", "password": "correct-horse-battery"}
    r1 = await client.post("/api/v1/auth/register", json=payload)
    assert r1.status_code == 201
    r2 = await client.post("/api/v1/auth/register", json=payload)
    assert r2.status_code == 409
    assert r2.json()["detail"]["error"]["code"] == "EMAIL_ALREADY_USED"


async def test_login_wrong_password(client):
    await client.post(
        "/api/v1/auth/register",
        json={"email": "b@example.com", "password": "correct-horse-battery"},
    )
    r = await client.post(
        "/api/v1/auth/login",
        json={"email": "b@example.com", "password": "wrong"},
    )
    assert r.status_code == 401
    assert r.json()["detail"]["error"]["code"] == "INVALID_CREDENTIALS"


async def test_login_success_case_insensitive_email(client):
    await client.post(
        "/api/v1/auth/register",
        json={"email": "Mixed@Example.COM", "password": "correct-horse-battery"},
    )
    r = await client.post(
        "/api/v1/auth/login",
        json={"email": "mixed@example.com", "password": "correct-horse-battery"},
    )
    assert r.status_code == 200
    assert r.json()["user"]["email"] == "mixed@example.com"


async def test_password_stored_as_argon2_hash(client):
    from sqlalchemy import select

    from app.db.base import get_sessionmaker
    from app.db.models import User

    await client.post(
        "/api/v1/auth/register",
        json={"email": "hash@example.com", "password": "correct-horse-battery"},
    )
    async with get_sessionmaker()() as s:
        user = (await s.execute(select(User).where(User.email == "hash@example.com"))).scalar_one()
    assert user.password_hash.startswith("$argon2id$")


# ---------------------------------------------------------------- Telegram initData


async def test_telegram_valid_init_data_creates_user(client):
    data = build_init_data(
        bot_token=BOT_TOKEN,
        user={"id": 777, "first_name": "Аня", "username": "anya"},
    )
    r = await client.post("/api/v1/auth/telegram", json={"init_data": data})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["user"]["telegram_id"] == 777
    assert body["user"]["telegram_username"] == "anya"
    assert body["user"]["email"] is None


async def test_telegram_second_call_returns_same_user(client):
    data = build_init_data(bot_token=BOT_TOKEN, user={"id": 555, "first_name": "X"})
    a = (await client.post("/api/v1/auth/telegram", json={"init_data": data})).json()
    data2 = build_init_data(bot_token=BOT_TOKEN, user={"id": 555, "first_name": "X"})
    b = (await client.post("/api/v1/auth/telegram", json={"init_data": data2})).json()
    assert a["user"]["id"] == b["user"]["id"]


async def test_telegram_expired_init_data_rejected(client):
    # auth_date старше 24 часов
    stale = int(time.time()) - (25 * 3600)
    data = build_init_data(bot_token=BOT_TOKEN, user={"id": 1, "first_name": "X"}, auth_date=stale)
    r = await client.post("/api/v1/auth/telegram", json={"init_data": data})
    assert r.status_code == 401
    assert r.json()["detail"]["error"]["code"] == "INIT_DATA_EXPIRED"


async def test_telegram_broken_hash_rejected(client):
    data = build_init_data(bot_token=BOT_TOKEN, user={"id": 1, "first_name": "X"})
    # Портим hash в конце — не совпадёт с секретным ключом
    tampered = data[:-4] + "dead"
    r = await client.post("/api/v1/auth/telegram", json={"init_data": tampered})
    assert r.status_code == 401
    assert r.json()["detail"]["error"]["code"] == "INVALID_INIT_DATA"


async def test_telegram_wrong_bot_token_rejected(client):
    # Подпись под другим токеном не должна проходить
    data = build_init_data(bot_token="000:OTHERBOTTOKEN", user={"id": 1, "first_name": "X"})
    r = await client.post("/api/v1/auth/telegram", json={"init_data": data})
    assert r.status_code == 401


# ---------------------------------------------------------------- refresh


async def _register(client, email="r@example.com"):
    r = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "correct-horse-battery"},
    )
    assert r.status_code == 201
    return r.json()


async def test_refresh_rotates_and_revokes_old(client):
    from sqlalchemy import select

    from app.core.security import hash_refresh_token
    from app.db.base import get_sessionmaker
    from app.db.models import Session

    tokens = await _register(client)
    old = tokens["refresh_token"]

    r = await client.post("/api/v1/auth/refresh", json={"refresh_token": old})
    assert r.status_code == 200
    new = r.json()["refresh_token"]
    assert new != old

    async with get_sessionmaker()() as s:
        old_row = (
            await s.execute(
                select(Session).where(Session.refresh_token_hash == hash_refresh_token(old))
            )
        ).scalar_one()
        assert old_row.revoked_at is not None
        new_row = (
            await s.execute(
                select(Session).where(Session.refresh_token_hash == hash_refresh_token(new))
            )
        ).scalar_one()
        assert new_row.revoked_at is None


async def test_refresh_reuse_of_revoked_kills_all_sessions(client):
    from sqlalchemy import select

    from app.db.base import get_sessionmaker
    from app.db.models import Session

    tokens = await _register(client)
    old = tokens["refresh_token"]
    # Первая ротация — old становится revoked
    r1 = await client.post("/api/v1/auth/refresh", json={"refresh_token": old})
    assert r1.status_code == 200
    still_valid_new = r1.json()["refresh_token"]

    # Повторное использование украденного (уже revoked) — сброс всех сессий
    r2 = await client.post("/api/v1/auth/refresh", json={"refresh_token": old})
    assert r2.status_code == 401
    assert r2.json()["detail"]["error"]["code"] == "REFRESH_REUSE_DETECTED"

    # Даже валидный не-отозванный refresh теперь не работает
    r3 = await client.post("/api/v1/auth/refresh", json={"refresh_token": still_valid_new})
    assert r3.status_code == 401

    async with get_sessionmaker()() as s:
        rows = (await s.execute(select(Session))).scalars().all()
        assert rows
        assert all(row.revoked_at is not None for row in rows)


async def test_refresh_unknown_token_rejected(client):
    r = await client.post("/api/v1/auth/refresh", json={"refresh_token": "nonexistent"})
    assert r.status_code == 401
    assert r.json()["detail"]["error"]["code"] == "INVALID_REFRESH_TOKEN"


async def test_refresh_expired_token_rejected(client):
    from datetime import datetime

    from sqlalchemy import update

    from app.core.security import hash_refresh_token
    from app.db.base import get_sessionmaker
    from app.db.models import Session

    tokens = await _register(client)
    refresh = tokens["refresh_token"]
    async with get_sessionmaker()() as s:
        await s.execute(
            update(Session)
            .where(Session.refresh_token_hash == hash_refresh_token(refresh))
            .values(expires_at=datetime.now(tz=UTC) - timedelta(days=1))
        )
        await s.commit()

    r = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh})
    assert r.status_code == 401


async def test_logout_revokes_session(client):
    from sqlalchemy import select

    from app.core.security import hash_refresh_token
    from app.db.base import get_sessionmaker
    from app.db.models import Session

    tokens = await _register(client)
    refresh = tokens["refresh_token"]
    r = await client.post("/api/v1/auth/logout", json={"refresh_token": refresh})
    assert r.status_code == 200
    async with get_sessionmaker()() as s:
        row = (
            await s.execute(
                select(Session).where(Session.refresh_token_hash == hash_refresh_token(refresh))
            )
        ).scalar_one()
        assert row.revoked_at is not None


# ---------------------------------------------------------------- consent


async def test_consent_requires_auth(client):
    r = await client.post("/api/v1/auth/consent", json={"version": "1.0"})
    assert r.status_code == 401


async def test_consent_sets_timestamp_and_version(client):
    from sqlalchemy import select

    from app.db.base import get_sessionmaker
    from app.db.models import User

    tokens = await _register(client, email="c@example.com")
    access = tokens["access_token"]
    r = await client.post(
        "/api/v1/auth/consent",
        json={"version": "1.0"},
        headers={"Authorization": f"Bearer {access}"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["consent_version"] == "1.0"
    assert body["consent_given_at"]

    async with get_sessionmaker()() as s:
        user = (await s.execute(select(User).where(User.email == "c@example.com"))).scalar_one()
        assert user.consent_version == "1.0"
        assert user.consent_given_at is not None


# ---------------------------------------------------------------- linking


async def test_link_token_confirm_attaches_email_to_tg_user(client):
    # 1. Логин в Telegram
    tg_data = build_init_data(bot_token=BOT_TOKEN, user={"id": 999, "first_name": "TG"})
    tg = (await client.post("/api/v1/auth/telegram", json={"init_data": tg_data})).json()
    tg_user_id = tg["user"]["id"]
    access = tg["access_token"]

    # 2. Создание токена привязки
    r = await client.post(
        "/api/v1/auth/link/create",
        json={"direction": "tg_to_web"},
        headers={"Authorization": f"Bearer {access}"},
    )
    assert r.status_code == 200
    token = r.json()["token"]

    # 3. Подтверждение с email+password → тот же аккаунт
    r2 = await client.post(
        "/api/v1/auth/link/confirm",
        json={"token": token, "email": "linked@example.com", "password": "correct-horse-battery"},
    )
    assert r2.status_code == 200, r2.text
    body = r2.json()
    assert body["user"]["id"] == tg_user_id
    assert body["user"]["email"] == "linked@example.com"


async def test_link_token_is_one_shot(client):
    tg_data = build_init_data(bot_token=BOT_TOKEN, user={"id": 1000, "first_name": "TG"})
    tg = (await client.post("/api/v1/auth/telegram", json={"init_data": tg_data})).json()
    access = tg["access_token"]

    token = (
        await client.post(
            "/api/v1/auth/link/create",
            json={"direction": "tg_to_web"},
            headers={"Authorization": f"Bearer {access}"},
        )
    ).json()["token"]

    r1 = await client.post(
        "/api/v1/auth/link/confirm",
        json={"token": token, "email": "once@example.com", "password": "correct-horse-battery"},
    )
    assert r1.status_code == 200
    r2 = await client.post(
        "/api/v1/auth/link/confirm",
        json={"token": token, "email": "twice@example.com", "password": "correct-horse-battery"},
    )
    assert r2.status_code == 400
    assert r2.json()["detail"]["error"]["code"] == "LINK_TOKEN_USED"


async def test_link_token_expires_after_15_minutes(client):
    # Всю цепочку делаем внутри freeze_time — иначе access-токен
    # окажется просроченным относительно замороженного времени.
    with freeze_time("2026-07-26 10:00:00") as frozen:
        tg_data = build_init_data(bot_token=BOT_TOKEN, user={"id": 1001, "first_name": "TG"})
        tg = (await client.post("/api/v1/auth/telegram", json={"init_data": tg_data})).json()
        access = tg["access_token"]

        token = (
            await client.post(
                "/api/v1/auth/link/create",
                json={"direction": "tg_to_web"},
                headers={"Authorization": f"Bearer {access}"},
            )
        ).json()["token"]

        frozen.move_to("2026-07-26 10:20:00")  # +20 минут — просрочен
        r = await client.post(
            "/api/v1/auth/link/confirm",
            json={"token": token, "email": "late@example.com", "password": "correct-horse-battery"},
        )
    assert r.status_code == 400
    assert r.json()["detail"]["error"]["code"] == "LINK_TOKEN_EXPIRED"


async def test_link_token_wrong_direction_rejected(client):
    # Создан как web_to_tg → но клиент пытается использовать его как tg_to_web
    reg = await _register(client, email="wrongdir@example.com")
    access = reg["access_token"]
    token = (
        await client.post(
            "/api/v1/auth/link/create",
            json={"direction": "web_to_tg"},
            headers={"Authorization": f"Bearer {access}"},
        )
    ).json()["token"]

    r = await client.post(
        "/api/v1/auth/link/confirm",
        json={"token": token, "email": "x@example.com", "password": "correct-horse-battery"},
    )
    assert r.status_code == 400
    assert r.json()["detail"]["error"]["code"] == "LINK_TOKEN_INVALID"
