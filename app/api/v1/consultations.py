
import uuid

from fastapi import APIRouter, Depends, Header, Request
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import current_user, get_request_id, require_role
from app.core.db import get_session
from app.core.errors import Conflict, NotFound
from app.core.metrics import IDEMPOTENT_REPLAYS
from app.models.consultation import Consultation
from app.models.user import User
from app.schemas.consultation import BookConsultationRequest, ConsultationOut
from app.services import booking as booking_svc
from app.services import consultation_state
from app.services import idempotency as idem_svc

router = APIRouter(prefix="/consultations", tags=["consultations"])


@router.post("", response_model=ConsultationOut, status_code=201)
async def book_consultation(
    req: BookConsultationRequest,
    request: Request,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    user: User = Depends(require_role("patient")),
    db: AsyncSession = Depends(get_session),
):
    body = await request.body()
    req_hash = idem_svc.compute_request_hash(
        request.method, request.url.path, body
    )

    # End the transaction started by authentication before starting
    # the atomic booking transaction.
    if db.in_transaction():
        await db.commit()

    async with db.begin():
        idem, replay = await idem_svc.acquire(
            db, user.id, idempotency_key, req_hash
        )

        if replay:
            IDEMPOTENT_REPLAYS.labels(route="/consultations").inc()
            response = JSONResponse(
                status_code=idem.response_status,
                content=idem.response_body,
            )
        else:
            consultation = await booking_svc.book(
                db,
                patient_id=user.id,
                slot_id=req.slot_id,
                idem=idem,
            )
            response = None

    if response is not None:
        return response

    await db.refresh(consultation)
    return consultation


@router.get("/me", response_model=list[ConsultationOut])
async def my_consultations(
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_session),
):
    stmt = (
        select(Consultation)
        .order_by(Consultation.created_at.desc())
        .limit(100)
    )

    if user.role == "patient":
        stmt = stmt.where(Consultation.patient_id == user.id)
    elif user.role == "doctor":
        from app.models.doctor import Doctor

        doctor = (
            await db.execute(
                select(Doctor).where(Doctor.user_id == user.id)
            )
        ).scalar_one_or_none()

        if doctor is None:
            return []

        stmt = stmt.where(Consultation.doctor_id == doctor.id)

    return (await db.execute(stmt)).scalars().all()


@router.get("/{consultation_id}", response_model=ConsultationOut)
async def get_consultation(
    consultation_id: uuid.UUID,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_session),
):
    consultation = await db.get(Consultation, consultation_id)

    if consultation is None:
        raise NotFound()

    if user.role == "patient" and consultation.patient_id != user.id:
        raise NotFound()

    if user.role == "doctor":
        from app.models.doctor import Doctor

        doctor = (
            await db.execute(
                select(Doctor).where(Doctor.user_id == user.id)
            )
        ).scalar_one_or_none()

        if doctor is None or consultation.doctor_id != doctor.id:
            raise NotFound()

    return consultation


async def _transition_endpoint(
    consultation_id, target, request, user, db
):
    consultation = await db.get(Consultation, consultation_id)

    if consultation is None:
        raise NotFound()

    if db.in_transaction():
        await db.commit()

    async with db.begin():
        await consultation_state.transition(
            db,
            consultation,
            target,
            user,
            request_id=get_request_id(request),
        )

    return {"status": consultation.status}


@router.post("/{consultation_id}/confirm")
async def confirm(
    consultation_id: uuid.UUID,
    request: Request,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_session),
):
    return await _transition_endpoint(
        consultation_id, "CONFIRMED", request, user, db
    )


@router.post("/{consultation_id}/start")
async def start(
    consultation_id: uuid.UUID,
    request: Request,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_session),
):
    return await _transition_endpoint(
        consultation_id, "IN_PROGRESS", request, user, db
    )


@router.post("/{consultation_id}/complete")
async def complete(
    consultation_id: uuid.UUID,
    request: Request,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_session),
):
    return await _transition_endpoint(
        consultation_id, "COMPLETED", request, user, db
    )


@router.post("/{consultation_id}/cancel")
async def cancel(
    consultation_id: uuid.UUID,
    request: Request,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_session),
):
    return await _transition_endpoint(
        consultation_id, "CANCELLED", request, user, db
    )
