import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import current_user, require_role
from app.core.db import get_session
from app.core.errors import Forbidden
from app.models.doctor import Doctor
from app.models.slot import AvailabilitySlot
from app.models.user import User
from app.schemas.doctor import DoctorOut
from app.schemas.slot import SlotCreate, SlotOut

router = APIRouter(prefix="/doctors", tags=["doctors"])


@router.get("", response_model=list[DoctorOut])
async def search_doctors(
    specialty: str | None = None,
    city: str | None = None,
    language: str | None = None,
    name: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_session),
):
    stmt = select(Doctor).where(Doctor.is_verified.is_(True))
    if specialty:
        stmt = stmt.where(Doctor.specialty == specialty)
    if city:
        stmt = stmt.where(Doctor.city == city)
    if language:
        stmt = stmt.where(Doctor.languages.any(language))
    stmt = stmt.order_by(Doctor.specialty, Doctor.id).offset((page - 1) * page_size).limit(page_size)
    rows = (await db.execute(stmt)).scalars().all()
    return rows


@router.get("/{doctor_id}/slots", response_model=list[SlotOut])
async def list_slots(
    doctor_id: uuid.UUID,
    from_: datetime | None = Query(None, alias="from"),
    to: datetime | None = Query(None),
    db: AsyncSession = Depends(get_session),
):
    stmt = select(AvailabilitySlot).where(
        AvailabilitySlot.doctor_id == doctor_id,
        AvailabilitySlot.is_booked.is_(False),
    )
    if from_:
        stmt = stmt.where(AvailabilitySlot.start_time >= from_)
    if to:
        stmt = stmt.where(AvailabilitySlot.start_time <= to)
    stmt = stmt.order_by(AvailabilitySlot.start_time).limit(200)
    return (await db.execute(stmt)).scalars().all()


@router.post("/{doctor_id}/slots", response_model=SlotOut, status_code=201)
async def create_slot(
    doctor_id: uuid.UUID,
    req: SlotCreate,
    user: User = Depends(require_role("doctor")),
    db: AsyncSession = Depends(get_session),
):
    doc = (await db.execute(select(Doctor).where(Doctor.id == doctor_id))).scalar_one_or_none()
    if not doc or doc.user_id != user.id:
        raise Forbidden("not_own_profile")
    slot = AvailabilitySlot(
        doctor_id=doctor_id,
        start_time=req.start_time,
        end_time=req.end_time,
    )
    db.add(slot)
    await db.commit()
    await db.refresh(slot)
    return slot
