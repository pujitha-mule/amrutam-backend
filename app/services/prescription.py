import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import Conflict, Forbidden
from app.models.audit import AuditLog
from app.models.consultation import Consultation
from app.models.doctor import Doctor
from app.models.prescription import Prescription
from app.models.user import User


async def issue(
    db: AsyncSession,
    *,
    consultation_id: uuid.UUID,
    actor: User,
    data: dict,
    request_id: str | None = None,
) -> Prescription:
    consult = (
        await db.execute(select(Consultation).where(Consultation.id == consultation_id))
    ).scalar_one_or_none()
    if not consult:
        raise Forbidden("consultation_not_accessible")  # 403 to not leak
    if actor.role != "doctor":
        raise Forbidden("only_doctor_can_prescribe")

    doctor = (await db.execute(select(Doctor).where(Doctor.user_id == actor.id))).scalar_one_or_none()
    if not doctor or doctor.id != consult.doctor_id:
        raise Forbidden("not_assigned_doctor")
    if consult.status != "COMPLETED":
        raise Conflict("consultation_not_completed")

    rx = Prescription(
        consultation_id=consult.id,
        patient_id=consult.patient_id,
        doctor_id=doctor.id,
        **data,
    )
    db.add(rx)
    db.add(
        AuditLog(
            actor_id=actor.id,
            action="prescription.issued",
            resource_type="prescription",
            resource_id=rx.id,
            outcome="success",
            request_id=request_id,
        )
    )
    await db.flush()
    return rx
