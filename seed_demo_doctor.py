import asyncio
from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.core.db import SessionLocal
from app.core.security import hash_password
from app.models.doctor import Doctor
from app.models.slot import AvailabilitySlot
from app.models.user import User


async def main():
    async with SessionLocal() as db:
        email = "doctor.demo@example.com"
        user = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()

        if user is None:
            user = User(
                email=email,
                password_hash=hash_password("DoctorDemo123!"),
                role="doctor",
                is_active=True,
                mfa_enabled=False,
            )
            db.add(user)
            await db.flush()

        doctor = (
            await db.execute(select(Doctor).where(Doctor.user_id == user.id))
        ).scalar_one_or_none()
        if doctor is None:
            doctor = Doctor(
                user_id=user.id,
                specialty="General Medicine",
                city="Hyderabad",
                languages=["English", "Telugu"],
                consultation_type="video",
                license_number="DEMO-LIC-0001",
                is_verified=True,
                bio="Local development test doctor",
            )
            db.add(doctor)
            await db.flush()

        slot = (
            (
                await db.execute(
                    select(AvailabilitySlot).where(
                        AvailabilitySlot.doctor_id == doctor.id,
                        AvailabilitySlot.is_booked.is_(False),
                    )
                )
            )
            .scalars()
            .first()
        )

        if slot is None:
            start = datetime.now(UTC) + timedelta(days=2)
            start = start.replace(minute=0, second=0, microsecond=0)
            slot = AvailabilitySlot(
                doctor_id=doctor.id,
                start_time=start,
                end_time=start + timedelta(minutes=30),
                is_booked=False,
            )
            db.add(slot)

        await db.commit()
        print("Doctor ID:", doctor.id)
        print("Slot ID:", slot.id)
        print("Slot start:", slot.start_time)
        print("Demo login:", email, "/ DoctorDemo123!")


asyncio.run(main())
