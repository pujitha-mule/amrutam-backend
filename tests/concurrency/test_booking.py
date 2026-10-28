import asyncio
import uuid
from datetime import UTC, datetime, timedelta

import pytest_asyncio

from app.models.slot import AvailabilitySlot


async def _register(client, email):
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "correct horse battery staple",
            "full_name": "P",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["access_token"]


@pytest_asyncio.fixture
async def slot(db, doctor_user):
    _, doctor = doctor_user

    slot = AvailabilitySlot(
        doctor_id=doctor.id,
        start_time=datetime.now(UTC) + timedelta(days=1),
        end_time=datetime.now(UTC) + timedelta(days=1, hours=1),
    )

    db.add(slot)
    await db.commit()
    await db.refresh(slot)

    return slot


async def test_two_patients_one_slot(client, slot):
    token_a = await _register(client, f"a{uuid.uuid4().hex[:6]}@t.com")
    token_b = await _register(client, f"b{uuid.uuid4().hex[:6]}@t.com")

    async def book(token, key):
        return await client.post(
            "/api/v1/consultations",
            json={"slot_id": str(slot.id)},
            headers={
                "Authorization": f"Bearer {token}",
                "Idempotency-Key": key,
            },
        )

    response_a, response_b = await asyncio.gather(
        book(token_a, "ka"),
        book(token_b, "kb"),
    )

    assert sorted([response_a.status_code, response_b.status_code]) == [201, 409]


async def test_same_key_same_body_replays(client, slot):
    token = await _register(client, f"r{uuid.uuid4().hex[:6]}@t.com")

    async def post():
        return await client.post(
            "/api/v1/consultations",
            json={"slot_id": str(slot.id)},
            headers={
                "Authorization": f"Bearer {token}",
                "Idempotency-Key": "same",
            },
        )

    response_1 = await post()
    response_2 = await post()

    assert response_1.status_code == 201, response_1.text
    assert response_2.status_code == 201, response_2.text
    assert response_1.json()["id"] == response_2.json()["id"]


async def test_same_key_different_body_409(client, slot, db, doctor_user):
    _, doctor = doctor_user

    other_slot = AvailabilitySlot(
        doctor_id=doctor.id,
        start_time=datetime.now(UTC) + timedelta(days=3),
        end_time=datetime.now(UTC) + timedelta(days=3, hours=1),
    )

    db.add(other_slot)
    await db.commit()
    await db.refresh(other_slot)

    token = await _register(client, f"x{uuid.uuid4().hex[:6]}@t.com")

    headers = {
        "Authorization": f"Bearer {token}",
        "Idempotency-Key": "conflict",
    }

    response_1 = await client.post(
        "/api/v1/consultations",
        json={"slot_id": str(slot.id)},
        headers=headers,
    )
    assert response_1.status_code == 201, response_1.text

    response_2 = await client.post(
        "/api/v1/consultations",
        json={"slot_id": str(other_slot.id)},
        headers=headers,
    )
    assert response_2.status_code == 409, response_2.text


async def test_cross_patient_access_returns_404(client, slot):
    token_a = await _register(client, f"p1{uuid.uuid4().hex[:6]}@t.com")
    token_b = await _register(client, f"p2{uuid.uuid4().hex[:6]}@t.com")

    response = await client.post(
        "/api/v1/consultations",
        json={"slot_id": str(slot.id)},
        headers={
            "Authorization": f"Bearer {token_a}",
            "Idempotency-Key": "x",
        },
    )
    assert response.status_code == 201, response.text

    consultation_id = response.json()["id"]

    other_response = await client.get(
        f"/api/v1/consultations/{consultation_id}",
        headers={"Authorization": f"Bearer {token_b}"},
    )

    assert other_response.status_code == 404


async def test_booking_missing_slot_returns_404(client):
    token = await _register(client, f"missing{uuid.uuid4().hex[:8]}@t.com")

    response = await client.post(
        "/api/v1/consultations",
        json={"slot_id": str(uuid.uuid4())},
        headers={
            "Authorization": f"Bearer {token}",
            "Idempotency-Key": f"missing-{uuid.uuid4().hex}",
        },
    )

    assert response.status_code == 404


async def test_booking_past_slot_returns_409(client, db, doctor_user):
    _, doctor = doctor_user
    past_slot = AvailabilitySlot(
        doctor_id=doctor.id,
        start_time=datetime.now(UTC) - timedelta(days=2),
        end_time=datetime.now(UTC) - timedelta(days=2) + timedelta(hours=1),
    )
    db.add(past_slot)
    await db.commit()
    await db.refresh(past_slot)

    token = await _register(client, f"past{uuid.uuid4().hex[:8]}@t.com")

    response = await client.post(
        "/api/v1/consultations",
        json={"slot_id": str(past_slot.id)},
        headers={
            "Authorization": f"Bearer {token}",
            "Idempotency-Key": f"past-{uuid.uuid4().hex}",
        },
    )

    assert response.status_code == 409
