"""Роутер /api/v1/me и /account — раздел 8.5 ТЗ."""

from __future__ import annotations

import csv
import io
import json
from datetime import UTC, date, datetime
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.base import get_db
from app.db.models import Cycle, DailyLog, User
from app.schemas.me import (
    AuthMethodEmail,
    AuthMethods,
    AuthMethodTelegram,
    ConsentInfo,
    ConsentTextOut,
    CycleHistoryItem,
    CycleStatus,
    DeleteAccountIn,
    EmailChangeIn,
    HistoryPage,
    LogHistoryItem,
    MeOut,
    MePatch,
    PasswordChangeIn,
    SessionOut,
    StatsOut,
)
from app.schemas.settings import PushSubscriptionOut
from app.services import me_service, predictions_service
from app.services.prediction import classify_regularity

router = APIRouter(tags=["me"])


def _err(exc) -> HTTPException:
    return HTTPException(
        status_code=exc.http_status,
        detail={"error": {"code": exc.code, "message": str(exc)}},
    )


# --------------------------------------------------------- /me core


async def _build_me_out(db: AsyncSession, user: User) -> MeOut:
    try:
        pred = await predictions_service.predict_for_user(db, user.id)
        cycle_status = CycleStatus(
            current_cycle_day=pred.current_cycle_day,
            days_until_period=pred.days_until_period,
            is_overdue=pred.is_overdue,
        )
    except predictions_service.NoDataError:
        cycle_status = CycleStatus()

    return MeOut(
        id=user.id,
        display_name=user.display_name,
        timezone=user.timezone,
        locale=user.locale,
        auth_methods=AuthMethods(
            telegram=AuthMethodTelegram(
                linked=user.telegram_id is not None,
                username=user.telegram_username,
            ),
            email=AuthMethodEmail(
                linked=user.email is not None,
                address=user.email,
                verified=user.email_verified_at is not None,
            ),
            password_set=user.password_hash is not None,
        ),
        consent=ConsentInfo(
            given_at=user.consent_given_at,
            version=user.consent_version,
        ),
        cycle_status=cycle_status,
        created_at=user.created_at,
    )


@router.get("/me", response_model=MeOut)
async def get_me(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> MeOut:
    return await _build_me_out(db, user)


@router.patch("/me", response_model=MeOut)
async def patch_me(
    body: MePatch,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> MeOut:
    data = body.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(user, k, v)
    await db.flush()
    return await _build_me_out(db, user)


# --------------------------------------------------------- login methods


@router.post("/me/email", status_code=status.HTTP_202_ACCEPTED)
async def change_email(
    body: EmailChangeIn,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    try:
        await me_service.set_or_change_email(db, user, email=body.email)
    except me_service.LastAuthMethodError as exc:
        raise _err(exc) from exc
    return {"ok": True, "email": user.email, "verified": True}


@router.post("/me/password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    body: PasswordChangeIn,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    try:
        await me_service.change_password(
            db, user, current_password=body.current_password, new_password=body.new_password
        )
    except me_service.InvalidCurrentPasswordError as exc:
        raise _err(exc) from exc


@router.delete("/me/telegram", status_code=status.HTTP_204_NO_CONTENT)
async def unlink_telegram(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    try:
        await me_service.unlink_telegram(db, user)
    except me_service.LastAuthMethodError as exc:
        raise _err(exc) from exc


@router.delete("/me/email", status_code=status.HTTP_204_NO_CONTENT)
async def unlink_email(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    try:
        await me_service.unlink_email(db, user)
    except me_service.LastAuthMethodError as exc:
        raise _err(exc) from exc


# --------------------------------------------------------- sessions


@router.get("/me/sessions", response_model=list[SessionOut])
async def list_sessions(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[SessionOut]:
    rows = await me_service.list_sessions(db, user.id)
    return [
        SessionOut(
            id=r.id,
            channel=r.channel.value,
            device_label=r.device_label,
            last_used_at=r.last_used_at,
            created_at=r.created_at,
        )
        for r in rows
    ]


@router.delete("/me/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_session(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    ok = await me_service.revoke_session(db, user.id, session_id)
    if not ok:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "SESSION_NOT_FOUND", "message": ""}},
        )


@router.delete("/me/sessions", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_all_sessions(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    # В MVP отзываем все сессии, включая текущую — user должен войти
    # заново на всех устройствах. Если позже понадобится «кроме текущей»,
    # передадим хеш текущего refresh через отдельный заголовок или
    # спрячем access-токен → session_id.
    await me_service.revoke_all_but(db, user.id, keep_hash=None)


@router.get("/push/subscriptions", response_model=list[PushSubscriptionOut])
async def list_push_subs(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[PushSubscriptionOut]:
    rows = await me_service.list_push_subscriptions(db, user.id)
    return [
        PushSubscriptionOut(
            id=str(r.id),
            endpoint=r.endpoint,
            user_agent=r.user_agent,
            is_active=r.is_active,
        )
        for r in rows
    ]


# --------------------------------------------------------- history


@router.get("/me/history/cycles", response_model=HistoryPage)
async def cycle_history(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> HistoryPage:
    total = await db.scalar(
        select(func.count()).select_from(Cycle).where(Cycle.user_id == user.id)
    )
    rows = await db.scalars(
        select(Cycle)
        .where(Cycle.user_id == user.id)
        .order_by(Cycle.start_date.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    items = [CycleHistoryItem.model_validate(c) for c in rows.all()]
    return HistoryPage(items=items, page=page, per_page=per_page, total=total or 0)


@router.get("/me/history/logs", response_model=HistoryPage)
async def logs_history(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    symptom: str | None = Query(default=None, max_length=32),
    from_: date | None = Query(default=None, alias="from"),
    to: date | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> HistoryPage:
    stmt = select(DailyLog).where(DailyLog.user_id == user.id)
    if from_ is not None:
        stmt = stmt.where(DailyLog.date >= from_)
    if to is not None:
        stmt = stmt.where(DailyLog.date <= to)
    if symptom:
        # ARRAY.contains — тег ищется как элемент массива symptoms
        stmt = stmt.where(DailyLog.symptoms.contains([symptom]))

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = await db.scalar(count_stmt)
    stmt = stmt.order_by(DailyLog.date.desc()).offset((page - 1) * per_page).limit(per_page)
    rows = (await db.scalars(stmt)).all()
    items = [
        LogHistoryItem(
            id=r.id,
            date=r.date,
            flow=r.flow.value if r.flow else None,
            mood=r.mood.value if r.mood else None,
            symptoms=r.symptoms,
            has_note=r.note is not None,
        )
        for r in rows
    ]
    return HistoryPage(items=items, page=page, per_page=per_page, total=total or 0)


@router.get("/me/consent", response_model=ConsentTextOut)
async def get_consent(
    user: User = Depends(get_current_user),
) -> ConsentTextOut:
    from pathlib import Path

    consent_path = Path("/app/docs/consent.md")
    text = consent_path.read_text() if consent_path.exists() else "Текст согласия — черновик."
    return ConsentTextOut(
        version=user.consent_version or "1.0",
        given_at=user.consent_given_at,
        text=text,
    )


# --------------------------------------------------------- export


@router.get("/export")
async def export_data(
    format: Literal["csv", "json"] = Query(default="json"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Response:
    cycles = (
        await db.scalars(
            select(Cycle).where(Cycle.user_id == user.id).order_by(Cycle.start_date)
        )
    ).all()
    logs = (
        await db.scalars(
            select(DailyLog).where(DailyLog.user_id == user.id).order_by(DailyLog.date)
        )
    ).all()

    if format == "json":
        payload = {
            "user_id": str(user.id),
            "exported_at": datetime.now(tz=UTC).isoformat(),
            "cycles": [
                {
                    "start_date": c.start_date.isoformat(),
                    "end_date": c.end_date.isoformat() if c.end_date else None,
                    "cycle_length": c.cycle_length,
                    "period_length": c.period_length,
                    "is_anomaly": c.is_anomaly,
                }
                for c in cycles
            ],
            "logs": [
                {
                    "date": r.date.isoformat(),
                    "flow": r.flow.value if r.flow else None,
                    "mood": r.mood.value if r.mood else None,
                    "symptoms": r.symptoms,
                    "note": r.note,
                }
                for r in logs
            ],
        }
        return Response(
            content=json.dumps(payload, ensure_ascii=False, indent=2),
            media_type="application/json",
            headers={"content-disposition": 'attachment; filename="myfaza-export.json"'},
        )

    # CSV: два блока в одном файле
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["# cycles"])
    w.writerow(["start_date", "end_date", "cycle_length", "period_length", "is_anomaly"])
    for c in cycles:
        w.writerow(
            [
                c.start_date.isoformat(),
                c.end_date.isoformat() if c.end_date else "",
                c.cycle_length or "",
                c.period_length or "",
                int(c.is_anomaly),
            ]
        )
    w.writerow([])
    w.writerow(["# logs"])
    w.writerow(["date", "flow", "mood", "symptoms", "note"])
    for r in logs:
        w.writerow(
            [
                r.date.isoformat(),
                r.flow.value if r.flow else "",
                r.mood.value if r.mood else "",
                ";".join(r.symptoms or []),
                (r.note or "").replace("\n", " "),
            ]
        )
    return Response(
        content=buf.getvalue(),
        media_type="text/csv",
        headers={"content-disposition": 'attachment; filename="myfaza-export.csv"'},
    )


# --------------------------------------------------------- privacy / delete


@router.post("/account/consent/revoke", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_consent(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    # FR-7.3: отзыв согласия → hard delete
    await me_service.hard_delete(db, user.id)


@router.delete("/account", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(
    body: DeleteAccountIn,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    if body.confirm != "DELETE":
        raise HTTPException(
            status_code=400,
            detail={"error": {"code": "BAD_CONFIRM", "message": "Ожидался confirm=DELETE"}},
        )
    await me_service.hard_delete(db, user.id)


# --------------------------------------------------------- stats


@router.get("/stats", response_model=StatsOut)
async def stats(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> StatsOut:
    # Все завершённые cycle_length за последние 12
    rows = (
        await db.scalars(
            select(Cycle.cycle_length)
            .where(Cycle.user_id == user.id, Cycle.cycle_length.is_not(None))
            .order_by(Cycle.start_date.desc())
            .limit(12)
        )
    ).all()
    lengths = [int(v) for v in rows if v is not None]

    periods = (
        await db.scalars(
            select(Cycle.period_length)
            .where(Cycle.user_id == user.id, Cycle.period_length.is_not(None))
            .order_by(Cycle.start_date.desc())
            .limit(12)
        )
    ).all()
    period_lens = [int(v) for v in periods if v is not None]

    avg_len = round(sum(lengths) / len(lengths)) if lengths else None
    avg_period = round(sum(period_lens) / len(period_lens)) if period_lens else None

    sigma_val = None
    if len(lengths) >= 2:
        from statistics import stdev

        sigma_val = round(stdev(lengths), 2)

    reg = classify_regularity(lengths[:6]) if len(lengths) >= 2 else None

    # FR-6.5: мягкое предупреждение. Никаких диагнозов.
    hint = None
    if lengths and any(v < 21 or v > 35 for v in lengths):
        hint = "Возможно, стоит обсудить это с врачом"
    if hint is None and period_lens and any(v > 8 for v in period_lens):
        hint = "Возможно, стоит обсудить это с врачом"

    return StatsOut(
        avg_cycle_length=avg_len,
        avg_period_length=avg_period,
        sigma=sigma_val,
        regularity=reg,
        last_lengths=list(reversed(lengths))[-12:],
        anomaly_hint=hint,
    )
