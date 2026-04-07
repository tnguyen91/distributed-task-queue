import sys

from celery import Celery

from src.app.core.config import settings

celery = Celery(
    "taskqueue",
    broker=settings.redis_url,
    include=["src.app.workers.task_handlers"],
)

celery.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    worker_pool="solo" if sys.platform == "win32" else "prefork",
)