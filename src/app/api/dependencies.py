from fastapi import Depends, HTTPException, Request
from redis.asyncio import Redis

from src.app.core.redis_client import get_redis
from src.app.services.rate_limit import check_rate_limit


def rate_limit(limit: int, window_seconds: int):
    """
    Build a FastAPI dependency that enforces a per-IP rate limit
    on the endpoint it's attached to.
    """

    async def dependency(
        request: Request,
        redis: Redis = Depends(get_redis),
    ) -> None:
        client_ip = request.client.host if request.client else "unknown"
        key = f"ratelimit:{client_ip}:{request.url.path}"

        allowed, remaining = await check_rate_limit(
            redis, key, limit=limit, window_seconds=window_seconds
        )

        if not allowed:
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded. Please try again later.",
                headers={
                    "Retry-After": str(window_seconds),
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": "0",
                },
            )

    return dependency