import uuid

import pytest


@pytest.mark.asyncio
async def test_register_success(client):
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": f"new-{uuid.uuid4().hex}@example.com",
            "password": "correct horse battery staple",
            "full_name": "New Patient",
            "phone": "9876543210",
        },
    )

    assert response.status_code == 201, response.text
    data = response.json()
    assert data["access_token"]
    assert data["refresh_token"]
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_register_duplicate_email(client):
    email = f"duplicate-{uuid.uuid4().hex}@example.com"
    payload = {
        "email": email,
        "password": "correct horse battery staple",
        "full_name": "Test Patient",
    }

    first = await client.post("/api/v1/auth/register", json=payload)
    assert first.status_code == 201, first.text

    second = await client.post("/api/v1/auth/register", json=payload)
    assert second.status_code == 409, second.text


@pytest.mark.asyncio
async def test_register_rejects_short_password(client):
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": f"short-{uuid.uuid4().hex}@example.com",
            "password": "short",
            "full_name": "Test Patient",
        },
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_login_invalid_password(client):
    registration = await client.post(
        "/api/v1/auth/register",
        json={
            "email": f"login-{uuid.uuid4().hex}@example.com",
            "password": "correct horse battery staple",
            "full_name": "Login Patient",
        },
    )
    assert registration.status_code == 201, registration.text

    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": registration.request.content.decode().split('"email": "')[-1].split('"')[0],
            "password": "wrong password",
        },
    )

    assert response.status_code == 401
from app.core.security import create_refresh_token, utcnow
from app.models.refresh_token import RefreshToken
from app.models.user import User


@pytest.mark.asyncio
async def test_login_success(client):
    email = f"success-{uuid.uuid4().hex}@example.com"
    registration = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "correct horse battery staple",
            "full_name": "Login Success",
        },
    )
    assert registration.status_code == 201, registration.text

    response = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "correct horse battery staple"},
    )

    assert response.status_code == 200, response.text
    assert response.json()["access_token"]
    assert response.json()["refresh_token"]


@pytest.mark.asyncio
async def test_login_disabled_account(client, db):
    email = f"disabled-{uuid.uuid4().hex}@example.com"
    registration = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "correct horse battery staple",
            "full_name": "Disabled User",
        },
    )
    assert registration.status_code == 201, registration.text

    from sqlalchemy import select

    user = (
        await db.execute(select(User).where(User.email == email))
    ).scalar_one()
    user.is_active = False
    await db.commit()

    response = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "correct horse battery staple"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "account_disabled"


@pytest.mark.asyncio
async def test_refresh_rotates_refresh_token(client, db):
    email = f"refresh-{uuid.uuid4().hex}@example.com"
    registration = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "correct horse battery staple",
            "full_name": "Refresh User",
        },
    )
    assert registration.status_code == 201, registration.text
    old_token = registration.json()["refresh_token"]

    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": old_token},
    )

    assert response.status_code == 200, response.text
    new_token = response.json()["refresh_token"]
    assert new_token
    assert new_token != old_token
from app.core.config import settings
from app.core.security import create_refresh_token


@pytest.mark.asyncio
async def test_refresh_rejects_invalid_token(client):
    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": "not-a-valid-token"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "invalid_refresh"


@pytest.mark.asyncio
async def test_refresh_rejects_revoked_token(client, db):
    email = f"revoked-{uuid.uuid4().hex}@example.com"
    registration = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "correct horse battery staple",
            "full_name": "Revoked User",
        },
    )
    assert registration.status_code == 201, registration.text

    from sqlalchemy import select

    user = (
        await db.execute(select(User).where(User.email == email))
    ).scalar_one()

    jti = uuid.uuid4().hex
    token = create_refresh_token(str(user.id), jti)
    row = RefreshToken(
        jti=jti,
        user_id=user.id,
        expires_at=utcnow().replace(year=utcnow().year + 1),
        revoked=True,
    )
    db.add(row)
    await db.commit()

    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": token},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "refresh_revoked"
@pytest.mark.asyncio
async def test_logout_revokes_refresh_token(client):
    email = f"logout-{uuid.uuid4().hex}@example.com"
    registration = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "correct horse battery staple",
            "full_name": "Logout User",
        },
    )
    assert registration.status_code == 201, registration.text
    refresh_token = registration.json()["refresh_token"]

    response = await client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": refresh_token},
    )
    assert response.status_code == 204

    reuse = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert reuse.status_code == 401
    assert reuse.json()["detail"] == "refresh_revoked"


@pytest.mark.asyncio
async def test_logout_invalid_token_returns_no_content(client):
    response = await client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": "invalid-token"},
    )

    assert response.status_code == 204

@pytest.mark.asyncio
async def test_mfa_enroll_returns_secret_and_uri(client, patient_token):
    response = await client.post(
        "/api/v1/auth/mfa/enroll",
        headers={"Authorization": f"Bearer {patient_token}"},
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["secret"]
    assert data["otpauth_uri"].startswith("otpauth://totp/")


@pytest.mark.asyncio
async def test_mfa_activate_rejects_invalid_code(client, patient_token):
    enrolled = await client.post(
        "/api/v1/auth/mfa/enroll",
        headers={"Authorization": f"Bearer {patient_token}"},
    )
    assert enrolled.status_code == 200, enrolled.text

    response = await client.post(
        "/api/v1/auth/mfa/activate",
        headers={"Authorization": f"Bearer {patient_token}"},
        json={"challenge_token": "unused", "code": "000000"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "invalid_totp"
