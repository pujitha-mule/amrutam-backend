import uuid

import pytest
import pytest_asyncio
from datetime import datetime, timedelta, timezone
from app.models.slot import AvailabilitySlot
from sqlalchemy import select

from app.core.errors import AppError
from app.models.audit import AuditLog
from app.models.consultation import Consultation
from app.models.doctor import Doctor
from app.models.user import User
from app.services.consultation_state import ALLOWED, transition


@pytest.mark.asyncio
async def test_allowed_transitions():
    assert ALLOWED["BOOKED"] == {"CONFIRMED", "CANCELLED"}
    assert ALLOWED["CONFIRMED"] == {"IN_PROGRESS", "CANCELLED"}
    assert ALLOWED["IN_PROGRESS"] == {"COMPLETED"}
    assert ALLOWED["COMPLETED"] == set()
    assert ALLOWED["CANCELLED"] == set()


@pytest.mark.asyncio
async def test_invalid_transition_raises_conflict(db, doctor_user, slot):
    user, doctor = doctor_user
    consultation = Consultation(
        patient_id=user.id,
        doctor_id=doctor.id,
        slot_id=slot.id,
        status="COMPLETED",
    )

    with pytest.raises(AppError) as exc:
        await transition(db, consultation, "CONFIRMED", user)

    assert exc.value.status_code == 409
    assert exc.value.detail == "invalid_transition_COMPLETED_to_CONFIRMED"


@pytest.mark.asyncio
async def test_patient_cannot_transition_another_patients_consultation(
    db, doctor_user, slot
):
    _, doctor = doctor_user
    patient_a = User(
        email=f"a{uuid.uuid4().hex}@test.com",
        password_hash="test-hash",
        role="patient",
    )
    patient_b = User(
        email=f"b{uuid.uuid4().hex}@test.com",
        password_hash="test-hash",
        role="patient",
    )
    db.add_all([patient_a, patient_b])
    await db.flush()

    consultation = Consultation(
        patient_id=patient_a.id,
        doctor_id=doctor.id,
        slot_id=slot.id,
        status="BOOKED",
    )
    db.add(consultation)
    await db.flush()

    with pytest.raises(AppError) as exc:
        await transition(db, consultation, "CANCELLED", patient_b)

    assert exc.value.status_code == 403
    assert exc.value.detail == "not_own_consultation"


@pytest.mark.asyncio
async def test_assigned_doctor_can_confirm_consultation(db, doctor_user, slot):
    doctor_user_obj, doctor = doctor_user
    patient = User(
        email=f"p{uuid.uuid4().hex}@test.com",
        password_hash="test-hash",
        role="patient",
    )
    db.add(patient)
    await db.flush()

    consultation = Consultation(
        patient_id=patient.id,
        doctor_id=doctor.id,
        slot_id=slot.id,
        status="BOOKED",
    )
    db.add(consultation)
    await db.flush()

    await transition(
        db, consultation, "CONFIRMED", doctor_user_obj,
        request_id="test-request",
    )

    assert consultation.status == "CONFIRMED"
    assert consultation.status_updated_at is not None
    assert consultation.status_updated_by == doctor_user_obj.id


@pytest.mark.asyncio
async def test_unassigned_doctor_is_forbidden(db, doctor_user, slot):
    _, doctor = doctor_user
    other_user = User(
        email=f"other{uuid.uuid4().hex}@test.com",
        password_hash="test-hash",
        role="doctor",
    )
    db.add(other_user)
    await db.flush()

    other_doctor = Doctor(
        user_id=other_user.id,
        specialty="cardiology",
        city="Hyderabad",
        license_number=f"LIC{uuid.uuid4().hex[:12]}",
        is_verified=True,
    )
    db.add(other_doctor)
    await db.flush()

    patient = User(
        email=f"patient{uuid.uuid4().hex}@test.com",
        password_hash="test-hash",
        role="patient",
    )
    db.add(patient)
    await db.flush()

    consultation = Consultation(
        patient_id=patient.id,
        doctor_id=doctor.id,
        slot_id=slot.id,
        status="BOOKED",
    )
    db.add(consultation)
    await db.flush()

    with pytest.raises(AppError) as exc:
        await transition(db, consultation, "CONFIRMED", other_user)

    assert exc.value.status_code == 403
    assert exc.value.detail == "not_assigned_doctor"


@pytest.mark.asyncio
async def test_transition_creates_audit_log(db, doctor_user, slot):
    _, doctor = doctor_user
    patient = User(
        email=f"patient{uuid.uuid4().hex}@test.com",
        password_hash="test-hash",
        role="patient",
    )
    db.add(patient)
    await db.flush()

    consultation = Consultation(
        patient_id=patient.id,
        doctor_id=doctor.id,
        slot_id=slot.id,
        status="BOOKED",
    )
    db.add(consultation)
    await db.flush()

    await transition(
        db, consultation, "CANCELLED", patient,
        request_id="audit-test",
    )
    await db.flush()

    audit = (
        await db.execute(
            select(AuditLog).where(
                AuditLog.resource_id == consultation.id,
                AuditLog.action == "consultation.cancelled",
            )
        )
    ).scalar_one()

    assert audit.actor_id == patient.id
    assert audit.outcome == "success"
    assert audit.request_id == "audit-test"


@pytest_asyncio.fixture
async def slot(db, doctor_user):
    _, doctor = doctor_user
    start = datetime.now(timezone.utc) + timedelta(days=1)
    slot = AvailabilitySlot(
        doctor_id=doctor.id,
        start_time=start,
        end_time=start + timedelta(hours=1),
    )
    db.add(slot)
    await db.commit()
    await db.refresh(slot)
    return slot
