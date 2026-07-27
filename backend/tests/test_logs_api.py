"""HTTP-тесты /logs — раздел 8.4 ТЗ."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta


async def _register(client, email="l@example.com") -> str:
    r = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "correct-horse-battery"},
    )
    return r.json()["access_token"]


def _auth(access: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {access}"}


async def test_upsert_and_get_log(client):
    access = await _register(client)
    today = datetime.now(tz=UTC).date()
    r = await client.put(
        f"/api/v1/logs/{today.isoformat()}",
        json={
            "flow": "medium",
            "mood": "good",
            "symptoms": ["Cramps", "cramps", " headache "],
            "note": "чувствую себя лучше",
        },
        headers=_auth(access),
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["flow"] == "medium"
    assert body["mood"] == "good"
    assert body["symptoms"] == ["cramps", "headache"]  # дедупликация + lower
    assert body["note"] == "чувствую себя лучше"

    # Второй PUT — обновление
    r2 = await client.put(
        f"/api/v1/logs/{today.isoformat()}",
        json={"flow": "light", "mood": "neutral", "symptoms": [], "note": None},
        headers=_auth(access),
    )
    assert r2.status_code == 200
    assert r2.json()["flow"] == "light"
    assert r2.json()["note"] is None


async def test_note_encrypted_at_rest(client):
    """Раздел 11.2: `daily_logs.note` шифруется на уровне приложения."""
    from sqlalchemy import select, text

    from app.db.base import get_sessionmaker
    from app.db.models import DailyLog

    access = await _register(client, email="crypt@example.com")
    today = datetime.now(tz=UTC).date()
    await client.put(
        f"/api/v1/logs/{today.isoformat()}",
        json={"note": "secret-plaintext"},
        headers=_auth(access),
    )
    async with get_sessionmaker()() as s:
        # Читаем raw через text() — если шифрование работает, plaintext не найдётся
        raw = (await s.execute(text("SELECT note FROM daily_logs LIMIT 1"))).scalar_one()
        assert raw is not None
        assert "secret-plaintext" not in raw
        # Через ORM должно расшифроваться обратно
        log = (await s.execute(select(DailyLog))).scalar_one()
        assert log.note == "secret-plaintext"


async def test_list_logs_range_filter(client):
    access = await _register(client)
    today = datetime.now(tz=UTC).date()
    for offset in (0, 5, 12):
        d = today - timedelta(days=offset)
        await client.put(
            f"/api/v1/logs/{d.isoformat()}",
            json={"mood": "neutral"},
            headers=_auth(access),
        )
    r = await client.get(
        "/api/v1/logs",
        params={"from": (today - timedelta(days=7)).isoformat(), "to": today.isoformat()},
        headers=_auth(access),
    )
    assert r.status_code == 200
    dates = {d["date"] for d in r.json()}
    assert (today - timedelta(days=12)).isoformat() not in dates
    assert today.isoformat() in dates


async def test_delete_log(client):
    access = await _register(client)
    today = datetime.now(tz=UTC).date()
    await client.put(
        f"/api/v1/logs/{today.isoformat()}",
        json={"mood": "good"},
        headers=_auth(access),
    )
    r = await client.delete(f"/api/v1/logs/{today.isoformat()}", headers=_auth(access))
    assert r.status_code == 204
    r2 = await client.delete(f"/api/v1/logs/{today.isoformat()}", headers=_auth(access))
    assert r2.status_code == 404


async def test_note_length_limit(client):
    access = await _register(client)
    today = datetime.now(tz=UTC).date()
    r = await client.put(
        f"/api/v1/logs/{today.isoformat()}",
        json={"note": "x" * 501},
        headers=_auth(access),
    )
    assert r.status_code == 422  # pydantic max_length


async def test_upsert_log_future_date_rejected(client):
    """Запись на будущую дату не сохраняется — 400 LOG_FUTURE."""
    access = await _register(client, email="future@x.com")
    tomorrow = datetime.now(tz=UTC).date() + timedelta(days=1)
    r = await client.put(
        f"/api/v1/logs/{tomorrow.isoformat()}",
        json={"mood": "good"},
        headers=_auth(access),
    )
    assert r.status_code == 400
    assert r.json()["detail"]["error"]["code"] == "LOG_FUTURE"


async def test_upsert_log_today_allowed(client):
    """Пограничный случай — сегодня разрешено."""
    access = await _register(client, email="today@x.com")
    today = datetime.now(tz=UTC).date()
    r = await client.put(
        f"/api/v1/logs/{today.isoformat()}",
        json={"mood": "good"},
        headers=_auth(access),
    )
    assert r.status_code == 200


async def test_logs_are_isolated_per_user(client):
    a = await _register(client, email="la@x.com")
    b = await _register(client, email="lb@x.com")
    today = datetime.now(tz=UTC).date()
    await client.put(
        f"/api/v1/logs/{today.isoformat()}",
        json={"mood": "good"},
        headers=_auth(a),
    )
    r = await client.get("/api/v1/logs", headers=_auth(b))
    assert r.status_code == 200
    assert r.json() == []
