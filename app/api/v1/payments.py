import uuid

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import current_user
from app.core.db import get_session
from app.core.errors import NotFound, Unauthorized
from app.core.security import verify_webhook_signature
from app.models.consultation import Consultation
from app.models.payment import Payment
from app.models.user import User
from app.schemas.payment import PaymentOut

router = APIRouter(tags=["payments"])


@router.post(
    "/consultations/{consultation_id}/payments", response_model=PaymentOut, status_code=201
)
async def create_payment(
    consultation_id: uuid.UUID,
    amount: float,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_session),
):
    c = await db.get(Consultation, consultation_id)
    if not c or c.patient_id != user.id:
        raise NotFound()
    payment = Payment(consultation_id=consultation_id, amount=amount, status="PENDING")
    db.add(payment)
    await db.commit()
    await db.refresh(payment)
    return payment


@router.post("/payments/webhook", status_code=200)
async def webhook(request: Request, db: AsyncSession = Depends(get_session)):
    raw = await request.body()
    sig = request.headers.get("x-signature", "")
    if not verify_webhook_signature(raw, sig):
        raise Unauthorized("invalid_signature")

    from sqlalchemy import text

    payload = await request.json()
    event_id = payload.get("event_id")
    if not event_id:
        raise Unauthorized("missing_event_id")

    # Dedupe
    r = await db.execute(
        text(
            "INSERT INTO processed_webhooks(provider_event_id) VALUES (:e) ON CONFLICT DO NOTHING"
        ),
        {"e": event_id},
    )
    if r.rowcount == 0:
        return {"status": "duplicate"}

    payment = await db.get(Payment, uuid.UUID(payload["payment_id"]))
    if payment:
        payment.status = payload["status"]
        payment.provider_reference = payload.get("provider_reference")
        await db.commit()
    return {"status": "ok"}
