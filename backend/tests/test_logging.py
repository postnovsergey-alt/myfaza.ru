"""Раздел 11.2: чувствительные поля не должны попадать в логи и Sentry."""
from app.core.logging import scrub, sentry_before_send


def test_scrub_removes_sensitive_fields():
    out = scrub({"user_id": "abc", "note": "личное", "start_date": "2026-07-01"})
    assert out["user_id"] == "abc"
    assert out["note"] == "[REDACTED]"
    assert out["start_date"] == "[REDACTED]"


def test_sentry_hook_scrubs_request():
    event = sentry_before_send({"request": {"symptoms": ["cramps"], "path": "/x"}}, None)
    assert event["request"]["symptoms"] == "[REDACTED]"
    assert event["request"]["path"] == "/x"
