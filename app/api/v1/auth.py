import secrets
import uuid

import pyotp
from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import current_user
from app.core.db import get_session
from app.core.errors import Conflict, Unauthorized
from app.core.rate_limit import rate_limit
from app.core.security import (
    create_access_token, create_mfa_challenge_token, create_refresh_token,
    decode_token, decrypt_mfa_secret, encrypt_mfa_secret, hash_password,
    utcnow, verify_password, verify_totp,
)
from app.core.config import settings
from app.models.profile import Profile
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.schemas.auth import (
    LoginRequest, MfaVerifyRequest, RefreshRequest, RegisterRequest, TokenResponse,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(
    req: RegisterRequest,
    request: Request,
    db: AsyncSession = Depends(get_session),
):
    await rate_limit(request, "register", limit=10, window_seconds=60)

    existing = (
        await db.execute(select(User).where(User.email == req.email))
    ).scalar_one_or_none()
    if existing:
        raise Conflict("email_taken")

    user = User(
        email=req.email,
        password_hash=hash_password(req.password),
        role="patient",
    )
    db.add(user)
    await db.flush()
    db.add(Profile(user_id=user.id, full_name=req.full_name, phone=req.phone))

    jti = secrets.token_hex(16)
    refresh = create_refresh_token(str(user.id), jti)
    db.add(RefreshToken(
        jti=jti, user_id=user.id,
        expires_at=utcnow().replace(year=utcnow().year + 1),
    ))
    await db.commit()

    return TokenResponse(
        access_token=create_access_token(str(user.id), user.role, "pwd"),
        refresh_token=refresh,
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    req: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_session),
):
    await rate_limit(request, "login", limit=20, window_seconds=60)

    user = (
        await db.execute(select(User).where(User.email == req.email))
    ).scalar_one_or_none()
    if not user or not verify_password(req.password, user.password_hash):
        raise Unauthorized("invalid_credentials")
    if not user.is_active:
        raise Unauthorized("account_disabled")

    if user.mfa_enabled:
        return TokenResponse(
            access_token="", refresh_token=None,
            mfa_required=True,
            challenge_token=create_mfa_challenge_token(str(user.id)),
        )

    jti = secrets.token_hex(16)
    refresh = create_refresh_token(str(user.id), jti)
    db.add(RefreshToken(
        jti=jti, user_id=user.id,
        expires_at=utcnow().replace(year=utcnow().year + 1),
    ))
    user.last_login_at = utcnow()
    await db.commit()

    return TokenResponse(
        access_token=create_access_token(str(user.id), user.role, "pwd"),
        refresh_token=refresh,
    )


@router.post("/mfa/verify", response_model=TokenResponse)
async def mfa_verify(req: MfaVerifyRequest, db: AsyncSession = Depends(get_session)):
    try:
        payload = decode_token(req.challenge_token)
    except ValueError:
        raise Unauthorized("invalid_challenge")
    if payload.get("type") != "mfa_challenge":
        raise Unauthorized("invalid_challenge_type")

    user = await db.get(User, uuid.UUID(payload["sub"]))
    if not user or not user.mfa_enabled or not user.mfa_secret_encrypted:
        raise Unauthorized("mfa_not_enrolled")

    if not verify_totp(decrypt_mfa_secret(user.mfa_secret_encrypted), req.code):
        raise Unauthorized("invalid_totp")

    jti = secrets.token_hex(16)
    refresh = create_refresh_token(str(user.id), jti)
    db.add(RefreshToken(
        jti=jti, user_id=user.id,
        expires_at=utcnow().replace(year=utcnow().year + 1),
    ))
    user.last_login_at = utcnow()
    await db.commit()

    return TokenResponse(
        access_token=create_access_token(str(user.id), user.role, "mfa"),
        refresh_token=refresh,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(req: RefreshRequest, db: AsyncSession = Depends(get_session)):
    try:
        payload = decode_token(req.refresh_token, settings.JWT_REFRESH_SECRET)
    except ValueError:
        raise Unauthorized("invalid_refresh")
    if payload.get("type") != "refresh":
        raise Unauthorized("wrong_token_type")

    row = await db.get(RefreshToken, payload["jti"])
    if not row or row.revoked:
        raise Unauthorized("refresh_revoked")

    user = await db.get(User, row.user_id)
    if not user or not user.is_active:
        raise Unauthorized("user_inactive")

    row.revoked = True
    jti = secrets.token_hex(16)
    new_refresh = create_refresh_token(str(user.id), jti)
    db.add(RefreshToken(
        jti=jti, user_id=user.id,
        expires_at=utcnow().replace(year=utcnow().year + 1),
    ))
    await db.commit()

    return TokenResponse(
        access_token=create_access_token(str(user.id), user.role, "pwd"),
        refresh_token=new_refresh,
    )


@router.post("/logout", status_code=204)
async def logout(req: RefreshRequest, db: AsyncSession = Depends(get_session)):
    try:
        payload = decode_token(req.refresh_token, settings.JWT_REFRESH_SECRET)
    except ValueError:
        return
    row = await db.get(RefreshToken, payload["jti"])
    if row:
        row.revoked = True
        await db.commit()


@router.post("/mfa/enroll")
async def mfa_enroll(user: User = Depends(current_user), db: AsyncSession = Depends(get_session)):
    secret = pyotp.random_base32()
    user.mfa_secret_encrypted = encrypt_mfa_secret(secret)
    await db.commit()
    uri = pyotp.TOTP(secret).provisioning_uri(name=user.email, issuer_name="Amrutam")
    return {"otpauth_uri": uri, "secret": secret}


@router.post("/mfa/activate")
async def mfa_activate(
    req: MfaVerifyRequest,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_session),
):
    if not user.mfa_secret_encrypted:
        raise Unauthorized("not_enrolled")
    if not verify_totp(decrypt_mfa_secret(user.mfa_secret_encrypted), req.code):
        raise Unauthorized("invalid_totp")
    user.mfa_enabled = True
    await db.commit()
    return {"status": "enabled"}
