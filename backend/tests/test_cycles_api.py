"""HTTP-тесты /cycles — раздел 8.2 ТЗ, валидация из FR-1.5."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta


async def _register(client, email="c@example.com") -> str:
    r = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "correct-horse-battery"},
    )
    assert r.status_code == 201
    return r.json()["access_token"]


def _auth(access: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {access}"}


async def test_create_and_list_cycle(client):
    access = await _register(client)
    today = datetime.now(tz=UTC).date()
    start = today - timedelta(days=5)
    r = await client.post(
        "/api/v1/cycles",
        json={"start_date": start.isoformat()},
        headers=_auth(access),
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["start_date"] == start.isoformat()
    assert body["is_anomaly"] is False

    lst = await client.get("/api/v1/cycles", headers=_auth(access))
    assert lst.status_code == 200
    assert len(lst.json()) == 1


async def test_create_cycle_in_the_future_rejected(client):
    access = await _register(client)
    tomorrow = (datetime.now(tz=UTC).date() + timedelta(days=1)).isoformat()
    r = await client.post(
        "/api/v1/cycles",
        json={"start_date": tomorrow},
        headers=_auth(access),
    )
    assert r.status_code == 400
    assert r.json()["detail"]["error"]["code"] == "CYCLE_FUTURE"


async def test_create_cycle_older_than_90d_rejected(client):
    access = await _register(client)
    old = (datetime.now(tz=UTC).date() - timedelta(days=100)).isoformat()
    r = await client.post(
        "/api/v1/cycles",
        json={"start_date": old},
        headers=_auth(access),
    )
    assert r.status_code == 400
    assert r.json()["detail"]["error"]["code"] == "CYCLE_TOO_OLD"


async def test_end_before_start_rejected(client):
    access = await _register(client)
    today = datetime.now(tz=UTC).date()
    r = await client.post(
        "/api/v1/cycles",
        json={
            "start_date": today.isoformat(),
            "end_date": (today - timedelta(days=1)).isoformat(),
        },
        headers=_auth(access),
    )
    assert r.status_code == 400
    assert r.json()["detail"]["error"]["code"] == "CYCLE_END_BEFORE_START"


async def test_overlapping_cycles_rejected(client):
    access = await _register(client)
    today = datetime.now(tz=UTC).date()
    await client.post(
        "/api/v1/cycles",
        json={
            "start_date": (today - timedelta(days=10)).isoformat(),
            "end_date": (today - timedelta(days=5)).isoformat(),
        },
        headers=_auth(access),
    )
    # Второй цикл пересекается по дате начала
    r = await client.post(
        "/api/v1/cycles",
        json={"start_date": (today - timedelta(days=7)).isoformat()},
        headers=_auth(access),
    )
    assert r.status_code == 400
    assert r.json()["detail"]["error"]["code"] == "CYCLE_OVERLAP"


async def test_period_length_out_of_range_marks_anomaly(client):
    """FR-1.5: длительность вне [1, 14] сохраняется, но с флагом is_anomaly."""
    access = await _register(client)
    today = datetime.now(tz=UTC).date()
    r = await client.post(
        "/api/v1/cycles",
        json={
            "start_date": (today - timedelta(days=20)).isoformat(),
            "end_date": (today - timedelta(days=5)).isoformat(),  # 16 дней
        },
        headers=_auth(access),
    )
    assert r.status_code == 201
    assert r.json()["is_anomaly"] is True
    assert r.json()["period_length"] == 16


async def test_end_current_cycle_computes_period_length(client):
    access = await _register(client)
    today = datetime.now(tz=UTC).date()
    start = today - timedelta(days=4)
    await client.post(
        "/api/v1/cycles",
        json={"start_date": start.isoformat()},
        headers=_auth(access),
    )
    r = await client.post(
        "/api/v1/cycles/current/end",
        json={"end_date": today.isoformat()},
        headers=_auth(access),
    )
    assert r.status_code == 200
    assert r.json()["end_date"] == today.isoformat()
    assert r.json()["period_length"] == 5


async def test_end_current_cycle_none_open(client):
    access = await _register(client)
    r = await client.post(
        "/api/v1/cycles/current/end",
        json={"end_date": datetime.now(tz=UTC).date().isoformat()},
        headers=_auth(access),
    )
    assert r.status_code == 400
    assert r.json()["detail"]["error"]["code"] == "NO_OPEN_CYCLE"


async def test_new_cycle_sets_cycle_length_on_previous(client):
    access = await _register(client)
    today = datetime.now(tz=UTC).date()
    prev_start = today - timedelta(days=30)
    r1 = await client.post(
        "/api/v1/cycles",
        json={
            "start_date": prev_start.isoformat(),
            "end_date": (prev_start + timedelta(days=4)).isoformat(),
        },
        headers=_auth(access),
    )
    prev_id = r1.json()["id"]

    await client.post(
        "/api/v1/cycles",
        json={"start_date": today.isoformat()},
        headers=_auth(access),
    )
    lst = await client.get("/api/v1/cycles", headers=_auth(access))
    prev = next(c for c in lst.json() if c["id"] == prev_id)
    assert prev["cycle_length"] == 30


async def test_patch_and_delete_cycle(client):
    access = await _register(client)
    today = datetime.now(tz=UTC).date()
    r = await client.post(
        "/api/v1/cycles",
        json={"start_date": (today - timedelta(days=3)).isoformat()},
        headers=_auth(access),
    )
    cid = r.json()["id"]

    p = await client.patch(
        f"/api/v1/cycles/{cid}",
        json={"end_date": today.isoformat()},
        headers=_auth(access),
    )
    assert p.status_code == 200
    assert p.json()["end_date"] == today.isoformat()

    d = await client.delete(f"/api/v1/cycles/{cid}", headers=_auth(access))
    assert d.status_code == 204
    lst = await client.get("/api/v1/cycles", headers=_auth(access))
    assert lst.json() == []


async def test_cycles_are_isolated_per_user(client):
    a = await _register(client, email="a@x.com")
    b = await _register(client, email="b@x.com")
    today = datetime.now(tz=UTC).date()
    await client.post(
        "/api/v1/cycles",
        json={"start_date": (today - timedelta(days=3)).isoformat()},
        headers=_auth(a),
    )
    lst_b = await client.get("/api/v1/cycles", headers=_auth(b))
    assert lst_b.status_code == 200
    assert lst_b.json() == []
