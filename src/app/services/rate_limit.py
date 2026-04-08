import logging
import time
import uuid

from redis.asyncio import Redis
from redis.exceptions import RedisError

logger = logging.getLogger(__name__)


async def check_rate_limit(
    redis: Redis,
    key: str,
    limit: int,
    window_seconds: int,
) -> tuple[bool, int]:
    """
    Sliding window rate limiter using Redis sorted sets.

    Returns (allowed, remaining). If Redis is unreachable, fails open
    by allowing the request through.
    """
    now = time.time()
    window_start = now - window_seconds
    member = f"{now}:{uuid.uuid4().hex}"

    try:
        pipe = redis.pipeline()
        pipe.zremrangebyscore(key, 0, window_start)
        pipe.zadd(key, {member: now})
        pipe.zcard(key)
        pipe.expire(key, window_seconds)
        results = await pipe.execute()
    except RedisError as exc:
        logger.warning("Rate limit check failed for %s: %s", key, exc)
        return True, limit  # Fail open

    current_count: int = results[2]

    if current_count > limit:
        # Roll back our addition so this rejected request does not
        # consume a slot for the entire window.
        try:
            await redis.zrem(key, member)
        except RedisError:
            pass
        return False, 0

    return True, limit - current_count