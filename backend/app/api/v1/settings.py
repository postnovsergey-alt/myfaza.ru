"""Роутер /api/v1/settings — раздел 8.5 ТЗ."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.base import get_db
from app.db.enums import NotifyChannel, Theme
from app.db.models import User
from app.schemas.settings import SettingsOut, SettingsPatch
from app.services import cycles_service

router = APIRouter(tags=["settings"])


@router.get("/settings", response_model=SettingsOut)
async def get_settings_ep(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> SettingsOut:
    row = await cycles_service.get_settings(db, user.id)
    return SettingsOut.model_validate(row)


@router.patch("/settings", response_model=SettingsOut)
async def patch_settings(
    body: SettingsPatch,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> SettingsOut:
    row = await cycles_service.get_settings(db, user.id)
    data = body.model_dump(exclude_unset=True)
    for k, v in data.items():
        if k == "notify_channel" and v is not None:
            setattr(row, k, NotifyChannel(v))
        elif k == "theme" and v is not None:
            setattr(row, k, Theme(v))
        else:
            setattr(row, k, v)
    await db.flush()
    await db.refresh(row)
    return SettingsOut.model_validate(row)
