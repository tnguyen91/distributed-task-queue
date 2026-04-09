import json
import logging

from redis import Redis as SyncRedis
from redis.asyncio import Redis as AsyncRedis
from redis.exceptions import RedisError

logger = logging.getLogger(__name__)

CHANNEL_PREFIX = "task_events:"


def channel_for(task_id: str) -> str:
    return f"{CHANNEL_PREFIX}{task_id}"


def publish_task_event_sync(redis: SyncRedis, task_id: str, payload: dict) -> None:
    """Publish from synchronous code (Celery workers)."""
    try:
        redis.publish(channel_for(task_id), json.dumps(payload, default=str))
    except RedisError as exc:
        logger.warning("Failed to publish event for %s: %s", task_id, exc)


async def publish_task_event_async(redis: AsyncRedis, task_id: str, payload: dict) -> None:
    """Publish from asynchronous code (API server)."""
    try:
        await redis.publish(channel_for(task_id), json.dumps(payload, default=str))
    except RedisError as exc:
        logger.warning("Failed to publish event for %s: %s", task_id, exc)