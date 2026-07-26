"""Роутер /api/v1/cycles — раздел 8.2 ТЗ."""

from __future__ import annotations

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.base import get_db
from app.db.enums import Source
from app.db.models import User
from app.schemas.cycles import CycleEnd, CycleIn, CycleOut, CyclePatch
from app.services import cycles_service

router = APIRouter(prefix="/cycles", tags=["cycles"])


def _err(exc: cycles_service.CycleValidationError) -> HTTPException:
    http = status.HTTP_404_NOT_FOUND if exc.code == "CYCLE_NOT_FOUND" else exc.http_status
    return HTTPException(
        status_code=http,
        detail={"error": {"code": exc.code, "message": exc.message}},
    )


@router.get("", response_model=list[CycleOut])
async def list_cycles(
    from_: date | None = Query(default=None, alias="from"),
    to: date | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[CycleOut]:
    cycles = await cycles_service.list_cycles(db, user.id, from_date=from_, to_date=to)
    return [CycleOut.model_validate(c) for c in cycles]


@router.post("", response_model=CycleOut, status_code=status.HTTP_201_CREATED)
async def create_cycle(
    body: CycleIn,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> CycleOut:
    try:
        cycle = await cycles_service.create_cycle(
            db, user, start=body.start_date, end=body.end_date, source=Source(body.source)
        )
    except cycles_service.CycleValidationError as exc:
        raise _err(exc) from exc
    return CycleOut.model_validate(cycle)


@router.patch("/{cycle_id}", response_model=CycleOut)
async def patch_cycle(
    cycle_id: UUID,
    body: CyclePatch,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> CycleOut:
    try:
        cycle = await cycles_service.update_cycle(
            db,
            user,
            cycle_id,
            start=body.start_date,
            end=body.end_date,
            end_provided="end_date" in body.model_fields_set,
        )
    except cycles_service.CycleValidationError as exc:
        raise _err(exc) from exc
    return CycleOut.model_validate(cycle)


@router.delete("/{cycle_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_cycle(
    cycle_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    try:
        await cycles_service.delete_cycle(db, user.id, cycle_id)
    except cycles_service.CycleValidationError as exc:
        raise _err(exc) from exc


@router.post("/current/end", response_model=CycleOut)
async def end_current(
    body: CycleEnd,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> CycleOut:
    try:
        cycle = await cycles_service.end_current_cycle(db, user, body.end_date)
    except cycles_service.CycleValidationError as exc:
        raise _err(exc) from exc
    return CycleOut.model_validate(cycle)
