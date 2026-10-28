from datetime import UTC, date, datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_mfa, require_role
from app.core.db import get_session
from app.models.consultation import Consultation
from app.models.payment import Payment
from app.models.user import User

router = APIRouter(prefix="/admin/analytics", tags=["admin"])


@router.get("/consultations")
async def consultation_stats(
    from_: date = Query(None, alias="from"),
    to: date = Query(None),
    user: User = Depends(require_role("admin")),
    _mfa: User = Depends(require_mfa),
    db: AsyncSession = Depends(get_session),
):
    stmt = select(Consultation.status, func.count()).group_by(Consultation.status)
    if from_:
        stmt = stmt.where(Consultation.created_at >= datetime.combine(from_, datetime.min, UTC))
    if to:
        stmt = stmt.where(Consultation.created_at <= datetime.combine(to, datetime.max, UTC))
    rows = (await db.execute(stmt)).all()
    return {"by_status": {s: c for s, c in rows}}


@router.get("/payments")
async def payment_stats(
    user: User = Depends(require_role("admin")),
    _mfa: User = Depends(require_mfa),
    db: AsyncSession = Depends(get_session),
):
    stmt = select(
        Payment.status, func.count(), func.coalesce(func.sum(Payment.amount), 0)
    ).group_by(Payment.status)
    rows = (await db.execute(stmt)).all()
    return {"by_status": [{"status": s, "count": c, "total": float(t)} for s, c, t in rows]}
