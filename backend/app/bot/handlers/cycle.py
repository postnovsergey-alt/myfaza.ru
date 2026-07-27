"""Callback-обработчики inline-кнопок из push-уведомлений (ТЗ 9.2).

`cyc:start:today` — отметить начало сегодня.
`cyc:start:yesterday` — отметить начало вчера.
`cyc:notyet` — пользователь отложил, ничего не создаём.
`cyc:end:today|yesterday|notyet` — закрытие менструации (ТЗ 3.5).
"""

from __future__ import annotations

import logging
from datetime import UTC, date, datetime, timedelta

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.enums import Source
from app.db.models import User
from app.services import cycles_service

router = Router(name="cycle")
log = logging.getLogger(__name__)


ACK_START = "Записала начало на {date}."
ACK_END = "Записала окончание на {date}."
ACK_NOTYET = "Ок, спрошу позже."
ACK_END_NOTYET = "Ок, спрошу через день."
ERR_NO_USER = "Не могу найти твой аккаунт — открой приложение через /start."
ERR_OVERLAP = "Похоже, эта дата уже отмечена. Проверь календарь в приложении."
ERR_GENERIC = "Не получилось сохранить. Попробуй ещё раз или отметь в приложении."


def _today() -> date:
    return datetime.now(tz=UTC).date()


def _fmt(d: date) -> str:
    months = [
        "января", "февраля", "марта", "апреля", "мая", "июня",
        "июля", "августа", "сентября", "октября", "ноября", "декабря",
    ]
    return f"{d.day} {months[d.month - 1]}"


async def _get_user(db: AsyncSession, tg_id: int) -> User | None:
    return await db.scalar(select(User).where(User.telegram_id == tg_id))


async def _reply_and_clear(cb: CallbackQuery, text: str) -> None:
    """Ответить пользователю, убрать кнопки — чтобы нельзя было нажать дважды."""
    await cb.answer(text, show_alert=False)
    msg = cb.message
    # InaccessibleMessage (сообщение старше 48ч) не поддерживает edit —
    # молча пропускаем: пользователь уже увидел toast от answer().
    if isinstance(msg, Message):
        try:
            await msg.edit_reply_markup(reply_markup=None)
        except Exception as exc:  # noqa: BLE001
            log.debug("edit_reply_markup failed: %s", exc)


@router.callback_query(F.data.in_({"cyc:start:today", "cyc:start:yesterday"}))
async def handle_start(cb: CallbackQuery, db: AsyncSession) -> None:
    if cb.from_user is None or cb.data is None:
        await cb.answer()
        return

    user = await _get_user(db, cb.from_user.id)
    if user is None:
        await _reply_and_clear(cb, ERR_NO_USER)
        return

    start = _today() if cb.data == "cyc:start:today" else _today() - timedelta(days=1)
    try:
        cycle = await cycles_service.create_cycle(
            db, user, start=start, end=None, source=Source.TELEGRAM
        )
    except cycles_service.CycleValidationError as exc:
        if exc.code == "CYCLE_OVERLAP":
            await _reply_and_clear(cb, ERR_OVERLAP)
        else:
            log.info("create_cycle rejected: %s", exc.code)
            await _reply_and_clear(cb, ERR_GENERIC)
        return

    await _reply_and_clear(cb, ACK_START.format(date=_fmt(cycle.start_date)))


@router.callback_query(F.data == "cyc:notyet")
async def handle_notyet(cb: CallbackQuery, db: AsyncSession) -> None:  # noqa: ARG001
    # По ТЗ 3.4: «Ещё нет» — переспросим через 2 дня. Пока просто квитируем,
    # логику повтора реализует планировщик.
    await _reply_and_clear(cb, ACK_NOTYET)


@router.callback_query(F.data.in_({"cyc:end:today", "cyc:end:yesterday"}))
async def handle_end(cb: CallbackQuery, db: AsyncSession) -> None:
    if cb.from_user is None or cb.data is None:
        await cb.answer()
        return

    user = await _get_user(db, cb.from_user.id)
    if user is None:
        await _reply_and_clear(cb, ERR_NO_USER)
        return

    end = _today() if cb.data == "cyc:end:today" else _today() - timedelta(days=1)
    try:
        cycle = await cycles_service.end_current_cycle(db, user, end)
    except cycles_service.CycleValidationError as exc:
        if exc.code == "NO_OPEN_CYCLE":
            await _reply_and_clear(cb, "Не вижу открытой менструации.")
        else:
            log.info("end_current_cycle rejected: %s", exc.code)
            await _reply_and_clear(cb, ERR_GENERIC)
        return
    assert cycle.end_date is not None
    await _reply_and_clear(cb, ACK_END.format(date=_fmt(cycle.end_date)))


@router.callback_query(F.data == "cyc:end:notyet")
async def handle_end_notyet(cb: CallbackQuery, db: AsyncSession) -> None:  # noqa: ARG001
    await _reply_and_clear(cb, ACK_END_NOTYET)
