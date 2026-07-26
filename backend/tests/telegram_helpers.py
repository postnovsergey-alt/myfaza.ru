"""Хелпер: сборка валидного Telegram initData под известный BOT_TOKEN.

Формула — из документации Telegram Bots WebApp:
1. secret_key = HMAC_SHA256(key="WebAppData", msg=bot_token)
2. data_check_string = "\\n".join(sorted("key=value" для всех кроме hash))
3. hash = HMAC_SHA256(secret_key, data_check_string).hex()
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from urllib.parse import urlencode


def build_init_data(
    *,
    bot_token: str,
    user: dict | None = None,
    auth_date: int | None = None,
    extra: dict | None = None,
) -> str:
    user = user or {"id": 42, "first_name": "Test", "username": "test_user"}
    payload: dict[str, str] = {
        "auth_date": str(auth_date if auth_date is not None else int(time.time())),
        "user": json.dumps(user, separators=(",", ":")),
        "query_id": "AAH1234567890",
    }
    if extra:
        payload.update(extra)

    data_check_string = "\n".join(f"{k}={payload[k]}" for k in sorted(payload))
    secret = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    h = hmac.new(secret, data_check_string.encode(), hashlib.sha256).hexdigest()

    payload["hash"] = h
    return urlencode(payload)
