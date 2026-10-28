from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import Conflict, Forbidden
from app.core.security import utcnow
from app.models.audit import AuditLog
from app.models.consultation import Consultation
from app.models.user import User

ALLOWED = {
    "BOOKED": {"CONFIRMED", "CANCELLED"},
    "CONFIRMED": {"IN_PROGRESS", "CANCELLED"},
    "IN_PROGRESS": {"COMPLETED"},
    "COMPLETED": set(),
    "CANCELLED": set(),
}


async def transition(
    db: AsyncSession,
    consultation: Consultation,
    target: str,
    actor: User,
    request_id: str | None = None,
):
    if target not in ALLOWED[consultation.status]:
        raise Conflict(f"invalid_transition_{consultation.status}_to_{target}")

    if actor.role == "doctor":
        # assigned doctor check
        from sqlalchemy import select

        from app.models.doctor import Doctor

        d = (
            await db.execute(select(Doctor).where(Doctor.user_id == actor.id))
        ).scalar_one_or_none()
        if not d or d.id != consultation.doctor_id:
            raise Forbidden("not_assigned_doctor")
    elif actor.role == "patient":
        if consultation.patient_id != actor.id:
            raise Forbidden("not_own_consultation")
    # admin can do anything valid

    consultation.status = target
    consultation.status_updated_at = utcnow()
    consultation.status_updated_by = actor.id

    db.add(
        AuditLog(
            actor_id=actor.id,
            action=f"consultation.{target.lower()}",
            resource_type="consultation",
            resource_id=consultation.id,
            outcome="success",
            request_id=request_id,
        )
    )
