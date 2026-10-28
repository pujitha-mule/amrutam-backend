import uuid

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import current_user, get_request_id
from app.core.db import get_session
from app.core.errors import NotFound
from app.models.doctor import Doctor
from app.models.prescription import Prescription
from app.models.user import User
from app.schemas.prescription import PrescriptionCreate, PrescriptionOut
from app.services import prescription as rx_svc

router = APIRouter(tags=["prescriptions"])


@router.post(
    "/consultations/{consultation_id}/prescriptions",
    response_model=PrescriptionOut,
    status_code=201,
)
async def issue_prescription(
    consultation_id: uuid.UUID,
    req: PrescriptionCreate,
    request: Request,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_session),
):
    if db.in_transaction():
        await db.commit()

    rx = await rx_svc.issue(
        db,
        consultation_id=consultation_id,
        actor=user,
        data=req.model_dump(),
        request_id=get_request_id(request),
    )

    await db.commit()
    await db.refresh(rx)
    return rx


@router.get(
    "/prescriptions/{prescription_id}",
    response_model=PrescriptionOut,
)
async def get_prescription(
    prescription_id: uuid.UUID,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_session),
):
    rx = await db.get(Prescription, prescription_id)

    if not rx:
        raise NotFound()

    if user.role == "patient" and rx.patient_id != user.id:
        raise NotFound()

    if user.role == "doctor":
        doctor = (
            await db.execute(select(Doctor).where(Doctor.user_id == user.id))
        ).scalar_one_or_none()

        if not doctor or rx.doctor_id != doctor.id:
            raise NotFound()

    return rx


@router.get(
    "/patients/me/prescriptions",
    response_model=list[PrescriptionOut],
)
async def my_prescriptions(
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_session),
):
    stmt = (
        select(Prescription)
        .where(Prescription.patient_id == user.id)
        .order_by(Prescription.issued_at.desc())
    )
    return (await db.execute(stmt)).scalars().all()
