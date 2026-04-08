import time
import logging
from datetime import datetime, timezone

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

import redis as sync_redis_lib

from src.app.core.config import settings
from src.app.models.task import Task
from src.app.schemas.task import TaskStatus
from src.app.workers.celery_app import celery
from src.app.services.cache import CACHE_KEY_PREFIX

logger = logging.getLogger(__name__)

sync_database_url = settings.database_url.replace("+asyncpg", "+psycopg2")
sync_engine = create_engine(sync_database_url)
SyncSession = sessionmaker(sync_engine)
sync_redis = sync_redis_lib.Redis.from_url(
    settings.redis_url,
    decode_responses=True,
)

def _invalidate_cache(task_id: str) -> None:
    try:
        sync_redis.delete(f"{CACHE_KEY_PREFIX}{task_id}")
    except sync_redis_lib.RedisError as exc:
        logger.warning("Failed to invalidate cache for %s: %s", task_id, exc)

def _execute_task(task_type: str, payload: dict) -> dict:
    # Simulation
    logger.info("Executing task type=%s", task_type)

    time.sleep(2)

    return {
        "message": f"Task '{task_type}' completed",
        "processed_at": datetime.now(timezone.utc).isoformat(),
        "input_keys": list(payload.keys()),
    }


@celery.task(
    bind=True,
    max_retries=None,
    acks_late=True,
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
)
def process_task(self, task_id: str):
    with SyncSession() as session:
        stmt = select(Task).where(Task.task_id == task_id)
        task = session.execute(stmt).scalar_one_or_none()

        if not task:
            logger.error("Task %s not found in database", task_id)
            return

        if task.status != TaskStatus.pending:
            logger.warning("Task %s has status %s, skipping", task_id, task.status)
            return

        # Mark as running
        task.status = TaskStatus.running
        task.started_at = datetime.now(timezone.utc)
        session.commit()
        _invalidate_cache(task_id)

        try:
            result = _execute_task(task.task_type, task.payload)

            task.status = TaskStatus.completed
            task.result = result
            task.completed_at = datetime.now(timezone.utc)
            session.commit()
            _invalidate_cache(task_id)
            logger.info("Task %s completed", task_id)

        except Exception as exc:
            task.retry_count += 1

            if task.retry_count >= task.max_retries:
                task.status = TaskStatus.failed
                task.error_message = str(exc)
                task.completed_at = datetime.now(timezone.utc)
                session.commit()
                _invalidate_cache(task_id)

                logger.error("Task %s failed permanently: %s", task_id, exc)
                return

            session.commit()
            _invalidate_cache(task_id)

            logger.warning(
                "Task %s failed (attempt %d/%d), retrying: %s",
                task_id, task.retry_count, task.max_retries, exc,
            )
            raise self.retry(exc=exc)
