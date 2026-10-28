import hashlib
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.errors import Conflict
from app.core.security import utcnow
from app.models.idempotency import IdempotencyRecord


def compute_request_hash(method: str, path: str, body: bytes) -> str:
    return hashlib.sha256(method.encode() + b"|" + path.encode() + b"|" + body).hexdigest()


async def acquire(
    db: AsyncSession, user_id, key: str, request_hash: str
) -> tuple[IdempotencyRecord, bool]:
    stmt = (
        select(IdempotencyRecord)
        .where(IdempotencyRecord.user_id == user_id, IdempotencyRecord.key == key)
        .with_for_update()
    )
    row = (await db.execute(stmt)).scalar_one_or_none()

    if row is None:
        row = IdempotencyRecord(
            user_id=user_id,
            key=key,
            request_hash=request_hash,
            created_at=utcnow(),
            expires_at=utcnow() + timedelta(hours=settings.IDEMPOTENCY_TTL_HOURS),
        )
        db.add(row)
        await db.flush()
        return row, False

    if row.request_hash != request_hash:
        raise Conflict("idempotency_key_reused_with_different_body")
    if row.response_status is None:
        raise Conflict("request_in_flight")
    return row, True
