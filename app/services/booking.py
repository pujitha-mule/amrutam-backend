import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import Conflict, NotFound
from app.core.metrics import BOOKING_CONFLICTS
from app.core.security import utcnow
from app.models.consultation import Consultation
from app.models.idempotency import IdempotencyRecord
from app.models.outbox import OutboxEvent
from app.models.slot import AvailabilitySlot


async def book(
    db: AsyncSession,
    *,
    patient_id: uuid.UUID,
    slot_id: uuid.UUID,
    idem: IdempotencyRecord,
) -> Consultation:
    async with db.begin_nested() if db.in_transaction() else db.begin():
        slot = (
            await db.execute(
                select(AvailabilitySlot).where(AvailabilitySlot.id == slot_id).with_for_update()
            )
        ).scalar_one_or_none()

        if slot is None:
            raise NotFound("slot_not_found")

        if slot.is_booked:
            BOOKING_CONFLICTS.labels(reason="already_booked").inc()
            raise Conflict("slot_already_booked")

        if slot.start_time <= utcnow():
            raise Conflict("slot_in_past")

        consultation = Consultation(
            patient_id=patient_id,
            doctor_id=slot.doctor_id,
            slot_id=slot.id,
            status="BOOKED",
        )

        db.add(consultation)

        # Generate the consultation UUID before creating its event.
        await db.flush()

        slot.is_booked = True
        slot.version += 1

        outbox_event = OutboxEvent(
            event_type="consultation.booked",
            aggregate_id=consultation.id,
            payload={
                "consultation_id": str(consultation.id),
                "patient_id": str(patient_id),
            },
        )
        db.add(outbox_event)

        try:
            await db.flush()
        except IntegrityError as e:
            if "ux_slot_active_consultation" in str(e.orig):
                BOOKING_CONFLICTS.labels(reason="unique_index_race").inc()
                raise Conflict("slot_already_booked") from e
            raise

        idem.response_status = 201
        idem.response_body = {
            "id": str(consultation.id),
            "status": consultation.status,
        }

    return consultation
