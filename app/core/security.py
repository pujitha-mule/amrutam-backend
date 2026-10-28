import base64
import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta

import pyotp
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, VerifyMismatchError
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from jose import JWTError, jwt

from app.core.config import settings

_ph = PasswordHasher(
    time_cost=settings.ARGON_TIME_COST,
    memory_cost=settings.ARGON_MEMORY_COST,
    parallelism=settings.ARGON_PARALLELISM,
)


def hash_password(password: str) -> str:
    return _ph.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    try:
        return _ph.verify(hashed, password)
    except (VerifyMismatchError, VerificationError):
        return False


def utcnow() -> datetime:
    return datetime.now(UTC)


def create_access_token(user_id: str, role: str, amr: str) -> str:
    now = utcnow()
    payload = {
        "sub": user_id,
        "role": role,
        "amr": amr,  # "pwd" or "mfa"
        "type": "access",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=settings.ACCESS_TOKEN_MINUTES)).timestamp()),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")


def create_refresh_token(user_id: str, jti: str) -> str:
    now = utcnow()
    payload = {
        "sub": user_id,
        "jti": jti,
        "type": "refresh",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(days=settings.REFRESH_TOKEN_DAYS)).timestamp()),
    }
    return jwt.encode(payload, settings.JWT_REFRESH_SECRET, algorithm="HS256")


def create_mfa_challenge_token(user_id: str) -> str:
    now = utcnow()
    payload = {
        "sub": user_id,
        "type": "mfa_challenge",
        "exp": int((now + timedelta(minutes=settings.MFA_CHALLENGE_MINUTES)).timestamp()),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")


def decode_token(token: str, secret: str = None) -> dict:
    try:
        return jwt.decode(token, secret or settings.JWT_SECRET, algorithms=["HS256"])
    except JWTError as e:
        raise ValueError(f"invalid token: {e}") from e


# --- MFA secret encryption (AES-GCM) ---


def _aes_key() -> bytes:
    return hashlib.sha256(settings.MFA_ENCRYPTION_KEY.encode()).digest()


def encrypt_mfa_secret(plaintext: str) -> str:
    aes = AESGCM(_aes_key())
    nonce = secrets.token_bytes(12)
    ct = aes.encrypt(nonce, plaintext.encode(), None)
    return base64.b64encode(nonce + ct).decode()


def decrypt_mfa_secret(encoded: str) -> str:
    raw = base64.b64decode(encoded)
    aes = AESGCM(_aes_key())
    return aes.decrypt(raw[:12], raw[12:], None).decode()


def verify_totp(secret_plaintext: str, code: str) -> bool:
    return pyotp.TOTP(secret_plaintext).verify(code, valid_window=1)


# --- webhook HMAC ---


def verify_webhook_signature(raw_body: bytes, signature: str) -> bool:
    expected = hmac.new(
        settings.PAYMENT_WEBHOOK_SECRET.encode(), raw_body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)
