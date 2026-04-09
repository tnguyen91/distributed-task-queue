import asyncio
import logging

from redis.asyncio import Redis
from redis.exceptions import RedisError

from src.app.services.events import channel_for

logger = logging.getLogger(__name__)


async def subscribe_to_task_events(redis: Redis, task_id: str):
    """
    Async generator yielding messages published to a task's channel.
    """
    pubsub = redis.pubsub()
    try:
        await pubsub.subscribe(channel_for(task_id))
        while True:
            try:
                message = await pubsub.get_message(
                    ignore_subscribe_messages=True,
                    timeout=1.0,
                )
            except RedisError as exc:
                logger.warning("Pubsub error for %s: %s", task_id, exc)
                break

            if message is None:
                yield None
                continue

            yield message["data"]
    finally:
        try:
            await pubsub.unsubscribe(channel_for(task_id))
            await pubsub.aclose()
        except Exception:
            pass