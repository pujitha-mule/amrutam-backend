import time

from fastapi import Request

from app.core.errors import AppError
from app.core.redis_client import get_redis


async def rate_limit(request: Request, bucket: str, limit: int, window_seconds: int):
    r = await get_redis()
    key = f"rl:{bucket}:{request.client.host if request.client else 'unknown'}"
    now = int(time.time())
    window_start = now - (now % window_seconds)
    redis_key = f"{key}:{window_start}"
    count = await r.incr(redis_key)
    if count == 1:
        await r.expire(redis_key, window_seconds + 1)
    if count > limit:
        raise AppError("rate_limited", 429)
