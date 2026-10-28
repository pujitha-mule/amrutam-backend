import uuid

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.errors import Forbidden, Unauthorized
from app.core.security import decode_token
from app.models.user import User

bearer = HTTPBearer(auto_error=False)


async def current_user(
    creds: HTTPAuthorizationCredentials = Depends(bearer),
    db: AsyncSession = Depends(get_session),
) -> User:
    if creds is None:
        raise Unauthorized("missing_token")
    try:
        payload = decode_token(creds.credentials)
    except ValueError:
        raise Unauthorized("invalid_token") from None

    if payload.get("type") != "access":
        raise Unauthorized("wrong_token_type")

    user = await db.get(User, uuid.UUID(payload["sub"]))
    if user is None or not user.is_active:
        raise Unauthorized("user_inactive")

    user._amr = payload.get("amr")
    return user


def require_role(*roles: str):
    async def _dep(user: User = Depends(current_user)) -> User:
        if user.role not in roles:
            raise Forbidden("role_forbidden")
        return user

    return _dep


def require_mfa(user: User = Depends(current_user)) -> User:
    if getattr(user, "_amr", None) != "mfa":
        raise Forbidden("mfa_required")
    return user


def get_request_id(request: Request) -> str:
    return request.headers.get("x-request-id", "-")
