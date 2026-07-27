"""Роутер /api/v1/logs — раздел 8.4 ТЗ."""

from __future__ import annotations

from datetime import date as date_cls

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.base import get_db
from app.db.models import User
from app.schemas.cycles import DailyLogIn, DailyLogOut
from app.services import logs_service

router = APIRouter(prefix="/logs", tags=["logs"])


@router.get("", response_model=list[DailyLogOut])
async def list_logs(
    from_: date_cls | None = Query(default=None, alias="from"),
    to: date_cls | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[DailyLogOut]:
    logs = await logs_service.list_logs(db, user.id, from_date=from_, to_date=to)
    return [DailyLogOut.model_validate(log) for log in logs]


@router.put("/{on}", response_model=DailyLogOut)
async def put_log(
    body: DailyLogIn,
    on: date_cls = Path(),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> DailyLogOut:
    try:
        log = await logs_service.upsert_log(
            db,
            user.id,
            on,
            flow=body.flow,
            mood=body.mood,
            symptoms=body.symptoms,
            note=body.note,
        )
    except logs_service.LogValidationError as exc:
        raise HTTPException(
            status_code=exc.http_status,
            detail={"error": {"code": exc.code, "message": exc.message}},
        ) from exc
    return DailyLogOut.model_validate(log)


@router.delete("/{on}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_log(
    on: date_cls = Path(),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    ok = await logs_service.delete_log(db, user.id, on)
    if not ok:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "LOG_NOT_FOUND", "message": "Запись за эту дату не найдена"}},
        )
