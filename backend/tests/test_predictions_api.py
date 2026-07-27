"""HTTP-тесты /predictions/next и /predictions/calendar."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta


async def _register(client, email="p@example.com") -> str:
    r = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "correct-horse-battery"},
    )
    return r.json()["access_token"]


def _auth(access: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {access}"}


async def test_next_prediction_404_when_no_cycles(client):
    access = await _register(client)
    r = await client.get("/api/v1/predictions/next", headers=_auth(access))
    assert r.status_code == 404
    assert r.json()["detail"]["error"]["code"] == "NO_CYCLES"


async def test_next_prediction_after_single_cycle(client):
    access = await _register(client)
    today = datetime.now(tz=UTC).date()
    await client.post(
        "/api/v1/cycles",
        json={"start_date": (today - timedelta(days=5)).isoformat()},
        headers=_auth(access),
    )
    r = await client.get("/api/v1/predictions/next", headers=_auth(access))
    assert r.status_code == 200
    body = r.json()
    assert body["confidence"] == "low"  # 0 завершённых
    assert body["margin_days"] == 5
    assert body["based_on_cycles"] == 0


async def test_calendar_marks_actual_and_predicted(client):
    access = await _register(client)
    today = datetime.now(tz=UTC).date()
    start = today - timedelta(days=3)
    await client.post(
        "/api/v1/cycles",
        json={
            "start_date": start.isoformat(),
            "end_date": today.isoformat(),
        },
        headers=_auth(access),
    )
    month = f"{today.year:04d}-{today.month:02d}"
    r = await client.get(
        "/api/v1/predictions/calendar",
        params={"month": month},
        headers=_auth(access),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["month"] == month
    states = {d["date"]: d["state"] for d in body["days"]}
    # start попал в фактическую менструацию
    assert states.get(start.isoformat()) == "period_actual"


async def test_calendar_bad_month_400(client):
    access = await _register(client)
    r = await client.get(
        "/api/v1/predictions/calendar",
        params={"month": "2026-13"},
        headers=_auth(access),
    )
    assert r.status_code == 422 or r.status_code == 400  # pydantic pattern


async def test_predictions_require_auth(client):
    r = await client.get("/api/v1/predictions/next")
    assert r.status_code == 401


async def test_is_period_active_freshly_marked_start(client):
    """Только-что-отмеченный старт → is_period_active=True."""
    access = await _register(client, "active1@example.com")
    today = datetime.now(tz=UTC).date()
    await client.post(
        "/api/v1/cycles",
        json={"start_date": today.isoformat()},
        headers=_auth(access),
    )
    r = await client.get("/api/v1/predictions/next", headers=_auth(access))
    assert r.status_code == 200
    assert r.json()["is_period_active"] is True


async def test_is_period_active_false_when_end_recorded(client):
    """Закрытый цикл (end_date заполнено) → is_period_active=False."""
    access = await _register(client, "active2@example.com")
    today = datetime.now(tz=UTC).date()
    await client.post(
        "/api/v1/cycles",
        json={
            "start_date": (today - timedelta(days=5)).isoformat(),
            "end_date": (today - timedelta(days=1)).isoformat(),
        },
        headers=_auth(access),
    )
    r = await client.get("/api/v1/predictions/next", headers=_auth(access))
    assert r.status_code == 200
    assert r.json()["is_period_active"] is False


async def test_is_period_active_false_when_stale_open_cycle(client):
    """Открытый цикл старше 14 дней → скорее забыли отметить конец,
    кнопку показывать не надо."""
    access = await _register(client, "active3@example.com")
    today = datetime.now(tz=UTC).date()
    await client.post(
        "/api/v1/cycles",
        json={"start_date": (today - timedelta(days=20)).isoformat()},
        headers=_auth(access),
    )
    r = await client.get("/api/v1/predictions/next", headers=_auth(access))
    assert r.status_code == 200
    assert r.json()["is_period_active"] is False


async def test_current_end_closes_cycle_and_clears_active(client):
    """POST /cycles/current/end закрывает цикл, следующий /predictions/next
    должен вернуть is_period_active=False."""
    access = await _register(client, "active4@example.com")
    today = datetime.now(tz=UTC).date()
    await client.post(
        "/api/v1/cycles",
        json={"start_date": (today - timedelta(days=3)).isoformat()},
        headers=_auth(access),
    )
    # был активен
    r = await client.get("/api/v1/predictions/next", headers=_auth(access))
    assert r.json()["is_period_active"] is True

    # закрываем
    r = await client.post(
        "/api/v1/cycles/current/end",
        json={"end_date": today.isoformat()},
        headers=_auth(access),
    )
    assert r.status_code == 200

    # больше не активен
    r = await client.get("/api/v1/predictions/next", headers=_auth(access))
    assert r.json()["is_period_active"] is False
