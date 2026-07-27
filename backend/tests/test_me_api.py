"""HTTP-тесты личного кабинета — раздел 8.5, FR-8, FR-7 ТЗ."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.db.base import get_sessionmaker
from app.db.models import Cycle, DailyLog, User


async def _register(client, email="me@example.com") -> str:
    r = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "correct-horse-battery"},
    )
    assert r.status_code == 201
    return r.json()["access_token"]


def _h(access: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {access}"}


async def test_me_returns_summary(client):
    access = await _register(client)
    r = await client.get("/api/v1/me", headers=_h(access))
    assert r.status_code == 200
    b = r.json()
    assert b["auth_methods"]["email"]["linked"] is True
    assert b["auth_methods"]["telegram"]["linked"] is False
    assert b["auth_methods"]["password_set"] is True


async def test_patch_me_updates_fields(client):
    access = await _register(client)
    r = await client.patch(
        "/api/v1/me",
        json={"display_name": "Аня", "timezone": "Asia/Vladivostok"},
        headers=_h(access),
    )
    assert r.status_code == 200
    assert r.json()["display_name"] == "Аня"
    assert r.json()["timezone"] == "Asia/Vladivostok"


async def test_change_password_requires_current(client):
    access = await _register(client)
    r = await client.post(
        "/api/v1/me/password",
        json={"new_password": "new-password-123"},
        headers=_h(access),
    )
    assert r.status_code == 400
    assert r.json()["detail"]["error"]["code"] == "INVALID_CURRENT_PASSWORD"


async def test_change_password_ok(client):
    access = await _register(client)
    r = await client.post(
        "/api/v1/me/password",
        json={"current_password": "correct-horse-battery", "new_password": "new-strong-pass-42"},
        headers=_h(access),
    )
    assert r.status_code == 204


async def test_unlink_email_when_only_method_rejected(client):
    access = await _register(client)
    r = await client.delete("/api/v1/me/email", headers=_h(access))
    assert r.status_code == 409
    assert r.json()["detail"]["error"]["code"] == "LAST_AUTH_METHOD"


async def test_unlink_email_ok_when_telegram_present(client):
    access = await _register(client)
    # Прикрутим telegram_id напрямую в БД
    sm = get_sessionmaker()
    async with sm() as s:
        user = (await s.execute(select(User).where(User.email == "me@example.com"))).scalar_one()
        user.telegram_id = 12345
        await s.commit()
    r = await client.delete("/api/v1/me/email", headers=_h(access))
    assert r.status_code == 204


async def test_sessions_list_and_revoke_one(client):
    access = await _register(client)
    r = await client.get("/api/v1/me/sessions", headers=_h(access))
    assert r.status_code == 200
    sessions = r.json()
    assert len(sessions) >= 1
    sid = sessions[0]["id"]
    r2 = await client.delete(f"/api/v1/me/sessions/{sid}", headers=_h(access))
    assert r2.status_code == 204


async def test_history_pagination(client):
    access = await _register(client)
    today = datetime.now(tz=UTC).date()
    # 3 цикла подряд
    for i in range(3):
        start = today - timedelta(days=30 * (3 - i))
        await client.post(
            "/api/v1/cycles",
            json={
                "start_date": start.isoformat(),
                "end_date": (start + timedelta(days=4)).isoformat(),
            },
            headers=_h(access),
        )
    r = await client.get("/api/v1/me/history/cycles?page=1&per_page=2", headers=_h(access))
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 3
    assert len(body["items"]) == 2


async def test_export_json(client):
    access = await _register(client)
    today = datetime.now(tz=UTC).date()
    await client.post(
        "/api/v1/cycles",
        json={"start_date": (today - timedelta(days=5)).isoformat()},
        headers=_h(access),
    )
    r = await client.get("/api/v1/export?format=json", headers=_h(access))
    assert r.status_code == 200
    assert "myfaza-export.json" in r.headers["content-disposition"]
    data = r.json()
    assert len(data["cycles"]) == 1


async def test_export_csv(client):
    access = await _register(client)
    r = await client.get("/api/v1/export?format=csv", headers=_h(access))
    assert r.status_code == 200
    assert "text/csv" in r.headers["content-type"]
    assert b"# cycles" in r.content


async def test_delete_account_wipes_all_related(client):
    """FR-7.2: hard delete всех связанных таблиц."""
    access = await _register(client)
    today = datetime.now(tz=UTC).date()
    await client.post(
        "/api/v1/cycles",
        json={"start_date": (today - timedelta(days=5)).isoformat()},
        headers=_h(access),
    )
    await client.put(
        f"/api/v1/logs/{today.isoformat()}",
        json={"mood": "good"},
        headers=_h(access),
    )
    r = await client.request(
        "DELETE", "/api/v1/account", json={"confirm": "DELETE"}, headers=_h(access)
    )
    assert r.status_code == 204

    sm = get_sessionmaker()
    async with sm() as s:
        users = (await s.execute(select(User).where(User.email == "me@example.com"))).all()
        cycles = (await s.execute(select(Cycle))).all()
        logs = (await s.execute(select(DailyLog))).all()
        assert users == []
        assert cycles == []
        assert logs == []


async def test_delete_account_requires_confirm(client):
    access = await _register(client)
    r = await client.request(
        "DELETE", "/api/v1/account", json={"confirm": "no"}, headers=_h(access)
    )
    assert r.status_code == 422  # pydantic Literal["DELETE"]


async def test_revoke_consent_deletes_account(client):
    """FR-7.3: отзыв согласия → каскадное удаление."""
    access = await _register(client, email="revoke@example.com")
    r = await client.post("/api/v1/account/consent/revoke", headers=_h(access))
    assert r.status_code == 204
    sm = get_sessionmaker()
    async with sm() as s:
        rows = (await s.execute(select(User).where(User.email == "revoke@example.com"))).all()
        assert rows == []


async def test_stats_empty(client):
    access = await _register(client)
    r = await client.get("/api/v1/stats", headers=_h(access))
    assert r.status_code == 200
    b = r.json()
    assert b["avg_cycle_length"] is None
    assert b["last_lengths"] == []


async def test_stats_with_cycles(client):
    access = await _register(client)
    today = datetime.now(tz=UTC).date()
    for i in range(4):
        start = today - timedelta(days=28 * (4 - i))
        await client.post(
            "/api/v1/cycles",
            json={
                "start_date": start.isoformat(),
                "end_date": (start + timedelta(days=4)).isoformat(),
            },
            headers=_h(access),
        )
    r = await client.get("/api/v1/stats", headers=_h(access))
    body = r.json()
    assert body["avg_cycle_length"] == 28
    assert body["regularity"] == "regular"
    assert body["anomaly_hint"] is None


async def test_stats_flags_anomaly_when_period_too_long(client):
    access = await _register(client)
    today = datetime.now(tz=UTC).date()
    start = today - timedelta(days=15)
    await client.post(
        "/api/v1/cycles",
        json={"start_date": start.isoformat(), "end_date": (start + timedelta(days=9)).isoformat()},
        headers=_h(access),
    )
    r = await client.get("/api/v1/stats", headers=_h(access))
    body = r.json()
    assert body["anomaly_hint"] is not None
