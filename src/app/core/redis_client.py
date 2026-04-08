from redis.asyncio import Redis

from src.app.core.config import settings

redis_client: Redis = Redis.from_url(
    settings.redis_url,
    decode_responses=True,
    health_check_interval=30,
)


async def get_redis() -> Redis:
    return redis_client