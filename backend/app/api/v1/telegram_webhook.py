"""POST /telegram/webhook — приём апдейтов от Telegram (ТЗ 8.7).

Секрет из настроек сравнивается с заголовком
`X-Telegram-Bot-Api-Secret-Token` через constant-time. Если совпало —
апдейт улетает в aiogram Dispatcher.
"""

from __future__ import annotations

import hmac
import logging
from typing import Annotated

from aiogram.types import Update
from fastapi import APIRouter, Header, HTTPException, Request, status

from app.bot.main import build_dispatcher, get_bot
from app.config import get_settings

router = APIRouter(prefix="/telegram", tags=["telegram"])
log = logging.getLogger(__name__)


@router.post("/webhook", status_code=status.HTTP_200_OK)
async def telegram_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: Annotated[str | None, Header()] = None,
) -> dict[str, str]:
    settings = get_settings()
    expected = settings.WEBHOOK_SECRET
    got = x_telegram_bot_api_secret_token or ""
    if not expected or not hmac.compare_digest(expected, got):
        # 401 — Telegram увидит ошибку и не будет флудить. В логах не пишем
        # тело (оно ушло от неподтверждённого источника — доверия ноль).
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="bad secret")

    try:
        payload = await request.json()
    except Exception as exc:  # noqa: BLE001
        log.warning("telegram webhook: bad json: %s", exc)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="bad json") from exc

    try:
        update = Update.model_validate(payload)
    except Exception as exc:  # noqa: BLE001
        log.warning("telegram webhook: invalid update payload: %s", exc)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="bad update") from exc

    dp = build_dispatcher()
    bot = get_bot()
    # feed_update принимает исключения на себя — мы всегда возвращаем 200,
    # чтобы Telegram не ретраил бесконечно на бажном хендлере.
    try:
        await dp.feed_update(bot, update)
    except Exception:  # noqa: BLE001
        log.exception("telegram webhook: handler crashed for update %s", update.update_id)
    return {"ok": "true"}
