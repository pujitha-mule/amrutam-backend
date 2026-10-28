import os
import uuid

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

# Configure test settings before importing the application.
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://amrutam:amrutam@localhost:5432/amrutam_test",
)
os.environ.setdefault("JWT_SECRET", "test")
os.environ.setdefault("JWT_REFRESH_SECRET", "test-refresh")
os.environ.setdefault(
    "MFA_ENCRYPTION_KEY",
    "0123456789abcdef0123456789abcdef",
)

from app.core.db import get_session
from app.main import app
from app.models import Base


@pytest_asyncio.fixture(autouse=True)
async def reset_redis_between_tests():
    from app.core.redis_client import get_redis, reset_redis

    # Close a Redis client left over from another test/event loop.
    await reset_redis()

    # Clear test Redis data, including any rate-limit counters.
    client = await get_redis()
    await client.flushdb()

    yield

    # Close the client before the next test's event loop.
    await reset_redis()


@pytest_asyncio.fixture
async def engine():
    from app.core.config import settings

    eng = create_async_engine(settings.DATABASE_URL)

    try:
        async with eng.begin() as conn:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS pgcrypto"))
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS btree_gist"))
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)

        yield eng
    finally:
        await eng.dispose()


@pytest_asyncio.fixture
async def db(engine):
    session_factory = async_sessionmaker(
        engine,
        expire_on_commit=False,
    )

    async with session_factory() as session:
        yield session


@pytest_asyncio.fixture
async def client(engine):
    session_factory = async_sessionmaker(
        engine,
        expire_on_commit=False,
    )

    async def override():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = override

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.pop(get_session, None)


@pytest_asyncio.fixture
async def patient_token(client):
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": f"p{uuid.uuid4().hex}@test.com",
            "password": "correct horse battery staple",
            "full_name": "Test Patient",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["access_token"]


@pytest_asyncio.fixture
async def doctor_user(db):
    from app.core.security import hash_password
    from app.models.doctor import Doctor
    from app.models.profile import Profile
    from app.models.user import User

    user = User(
        email=f"d{uuid.uuid4().hex}@test.com",
        password_hash=hash_password("x" * 15),
        role="doctor",
    )

    db.add(user)
    await db.flush()

    db.add(Profile(user_id=user.id, full_name="Dr Test"))

    doctor = Doctor(
        user_id=user.id,
        specialty="dermatology",
        city="Hyderabad",
        license_number=f"LIC{uuid.uuid4().hex[:12]}",
        is_verified=True,
    )

    db.add(doctor)
    await db.commit()
    await db.refresh(doctor)

    return user, doctor
