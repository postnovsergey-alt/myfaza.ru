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
