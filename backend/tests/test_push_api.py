"""HTTP-тесты /push и /settings."""

from __future__ import annotations


async def _register(client, email="pu@example.com") -> str:
    r = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "correct-horse-battery"},
    )
    return r.json()["access_token"]


def _auth(access: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {access}"}


async def test_subscribe_and_unsubscribe(client):
    access = await _register(client)
    r = await client.post(
        "/api/v1/push/subscribe",
        json={"endpoint": "https://push.example/abc", "keys": {"p256dh": "P", "auth": "A"}},
        headers=_auth(access),
    )
    assert r.status_code == 201, r.text
    assert r.json()["id"]

    r2 = await client.post(
        "/api/v1/push/unsubscribe",
        json={"endpoint": "https://push.example/abc"},
        headers=_auth(access),
    )
    assert r2.status_code == 204


async def test_subscribe_upserts_by_endpoint(client):
    access = await _register(client)
    body = {"endpoint": "https://push.example/x", "keys": {"p256dh": "P", "auth": "A"}}
    r1 = await client.post("/api/v1/push/subscribe", json=body, headers=_auth(access))
    r2 = await client.post("/api/v1/push/subscribe", json=body, headers=_auth(access))
    # Один и тот же endpoint — два раза не создаётся, id одинаковый
    assert r1.json()["id"] == r2.json()["id"]


async def test_vapid_key_endpoint(client, monkeypatch):
    from app.config import get_settings

    monkeypatch.setenv("VAPID_PUBLIC_KEY", "TESTPUBKEY")
    get_settings.cache_clear()
    r = await client.get("/api/v1/push/vapid-key")
    assert r.status_code == 200
    assert r.json()["public_key"] == "TESTPUBKEY"
    get_settings.cache_clear()


async def test_settings_patch_updates_and_returns(client):
    access = await _register(client)
    r = await client.patch(
        "/api/v1/settings",
        json={"notify_before_days": 5, "notify_channel": "web", "discreet_mode": False},
        headers=_auth(access),
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["notify_before_days"] == 5
    assert body["notify_channel"] == "web"
    assert body["discreet_mode"] is False


async def test_settings_validation_rejects_bad_range(client):
    access = await _register(client)
    r = await client.patch(
        "/api/v1/settings",
        json={"notify_before_days": 10},  # ge=1 le=7
        headers=_auth(access),
    )
    assert r.status_code == 422
