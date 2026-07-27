"""Обработчик /start и /start link_<token>.

ТЗ 3.1 (приветствие + ссылка на политику) и 3.3 (обратная привязка
web→tg по deep-link `t.me/<bot>?start=link_<token>`).
"""

from __future__ import annotations

import logging

from aiogram import Router
from aiogram.filters import CommandObject, CommandStart
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot import keyboards
from app.config import get_settings
from app.services import auth_service

router = Router(name="start")
log = logging.getLogger(__name__)


WELCOME = (
    "Привет! Я — «Моя фаза», помогу отслеживать цикл.\n\n"
    "Данные — специальная категория ПДн (152-ФЗ, ст. 10), поэтому "
    "перед первым использованием ознакомься с политикой:\n"
    "{privacy_url}\n\n"
    "Нажми кнопку ниже, чтобы открыть приложение и завершить онбординг."
)

LINK_OK = "Готово — аккаунт привязан. Открой приложение, данные подтянутся."
LINK_EXPIRED = "Ссылка привязки истекла или уже использована. Сгенерируй новую в приложении."
LINK_ALREADY_TAKEN = "Этот Telegram уже привязан к другому аккаунту."
LINK_FAILED = "Не получилось привязать. Попробуй сгенерировать новую ссылку."


@router.message(CommandStart(deep_link=True))
async def start_with_payload(
    message: Message, command: CommandObject, db: AsyncSession
) -> None:
    payload = (command.args or "").strip()
    if payload.startswith("link_"):
        await _handle_link(message, payload.removeprefix("link_"), db)
        return
    # Неизвестный payload — обрабатываем как обычный /start
    await _handle_plain_start(message, db)


@router.message(CommandStart())
async def start_plain(message: Message, db: AsyncSession) -> None:
    await _handle_plain_start(message, db)


async def _safe_answer(message: Message, text: str, **kwargs) -> None:
    """Ответ пользователю не должен рушить транзакцию.

    Если Telegram отвечает 4xx (chat not found, blocked и т.п.) — сохранение
    user/цикла всё равно должно закоммититься. Лог + swallow.
    """
    try:
        await message.answer(text, **kwargs)
    except Exception as exc:  # noqa: BLE001
        log.warning("bot answer failed for chat %s: %s", message.chat.id, exc)


async def _handle_plain_start(message: Message, db: AsyncSession) -> None:
    settings = get_settings()
    tg = message.from_user
    if tg is not None:
        # Создаём/обновляем пользователя, чтобы push-уведомления знали, кому слать
        try:
            await auth_service.authenticate_telegram(
                db, telegram_id=tg.id, username=tg.username
            )
        except auth_service.AuthError as exc:
            log.warning("authenticate_telegram failed on /start: %s", exc)

    text = WELCOME.format(privacy_url=f"https://{settings.PUBLIC_DOMAIN}/privacy")
    await _safe_answer(message, text, reply_markup=keyboards.open_app_button())


async def _handle_link(message: Message, token: str, db: AsyncSession) -> None:
    tg = message.from_user
    if tg is None:
        await _safe_answer(message, LINK_FAILED)
        return
    try:
        await auth_service.confirm_link_telegram(
            db, token=token, telegram_id=tg.id, username=tg.username
        )
    except auth_service.LinkTokenInvalidError:
        await _safe_answer(message, LINK_EXPIRED)
        return
    except auth_service.EmailAlreadyUsedError:
        # confirm_link_telegram переиспользует код TELEGRAM_ALREADY_USED
        await _safe_answer(message, LINK_ALREADY_TAKEN)
        return
    except auth_service.AuthError as exc:
        log.warning("confirm_link_telegram failed: %s", exc)
        await _safe_answer(message, LINK_FAILED)
        return

    await _safe_answer(message, LINK_OK, reply_markup=keyboards.open_app_button())
