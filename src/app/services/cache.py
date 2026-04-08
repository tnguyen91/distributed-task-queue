import logging

from redis.asyncio import Redis
from redis.exceptions import RedisError

from src.app.schemas.task import TaskResponse

logger = logging.getLogger(__name__)

CACHE_TTL_SECONDS = 10
CACHE_KEY_PREFIX = "task:"


def _cache_key(task_id: str) -> str:
    return f"{CACHE_KEY_PREFIX}{task_id}"


async def get_cached_task(redis: Redis, task_id: str) -> TaskResponse | None:
    try:
        raw = await redis.get(_cache_key(task_id))
    except RedisError as exc:
        logger.warning("Redis read failed for %s: %s", task_id, exc)
        return None

    if raw is None:
        return None

    try:
        return TaskResponse.model_validate_json(raw)
    except ValueError as exc:
        logger.warning("Cached value for %s is corrupt: %s", task_id, exc)
        return None


async def cache_task(redis: Redis, task: TaskResponse) -> None:
    """Write a task into the cache with a short TTL."""
    try:
        await redis.set(
            _cache_key(task.task_id),
            task.model_dump_json(),
            ex=CACHE_TTL_SECONDS,
        )
    except RedisError as exc:
        logger.warning("Redis write failed for %s: %s", task.task_id, exc)


async def invalidate_task_cache(redis: Redis, task_id: str) -> None:
    """Delete a task from the cache."""
    try:
        await redis.delete(_cache_key(task_id))
    except RedisError as exc:
        logger.warning("Redis delete failed for %s: %s", task_id, exc)