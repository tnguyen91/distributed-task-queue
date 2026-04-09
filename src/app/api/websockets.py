import asyncio
import logging

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from redis.asyncio import Redis

from src.app.core.redis_client import get_redis
from src.app.services.event_stream import subscribe_to_task_events

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/tasks/ws", tags=["websockets"])


@router.websocket("/{task_id}")
async def task_event_stream(
    websocket: WebSocket,
    task_id: str,
    redis: Redis = Depends(get_redis),
):
    await websocket.accept()
    logger.info("WebSocket connected for task %s", task_id)

    # Signal set when the client sends a CLOSE frame.
    disconnected = asyncio.Event()

    async def _watch_disconnect() -> None:
        try:
            while True:
                msg = await websocket.receive()
                if msg.get("type") == "websocket.disconnect":
                    break
        except Exception:
            pass
        disconnected.set()

    disconnect_task = asyncio.create_task(_watch_disconnect())

    pubsub_gen = subscribe_to_task_events(redis, task_id)
    try:
        async for message in pubsub_gen:
            if disconnected.is_set():
                break

            if message is None:
                # Heartbeat tick: confirm the client is still connected
                try:
                    await websocket.send_text('{"type":"ping"}')
                except Exception:
                    break
                continue

            try:
                await websocket.send_text(message)
            except Exception:
                break
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected for task %s", task_id)
    except Exception as exc:
        logger.exception("WebSocket error for task %s: %s", task_id, exc)
    finally:
        disconnect_task.cancel()
        await pubsub_gen.aclose()
        try:
            await websocket.close()
        except Exception:
            pass