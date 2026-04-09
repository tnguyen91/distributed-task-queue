import secrets
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from redis.asyncio import Redis
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.api.dependencies import rate_limit
from src.app.core.deps import get_db
from src.app.core.redis_client import get_redis
from src.app.models.task import Task
from src.app.schemas.task import (
    PaginationMeta,
    TaskCreate,
    TaskListResponse,
    TaskPriority,
    TaskResponse,
    TaskStatus,
)
from src.app.services.cache import (
    cache_task,
    get_cached_task,
    invalidate_task_cache,
)
from src.app.workers.task_handlers import process_task
from src.app.core.metrics import tasks_submitted_total

router = APIRouter(prefix="/api/v1/tasks", tags=["tasks"])


def _generate_task_id() -> str:
    return f"tsk_{secrets.token_hex(8)}"


def _row_to_response(task: Task) -> TaskResponse:
    return TaskResponse(
        task_id=task.task_id,
        status=task.status,
        task_type=task.task_type,
        payload=task.payload,
        result=task.result,
        error_message=task.error_message,
        priority=task.priority,
        max_retries=task.max_retries,
        retry_count=task.retry_count,
        created_at=task.created_at,
        started_at=task.started_at,
        completed_at=task.completed_at,
    )


@router.post(
    "",
    status_code=202,
    response_model=TaskResponse,
    dependencies=[Depends(rate_limit(limit=10, window_seconds=60))],
)
async def submit_task(body: TaskCreate, db: AsyncSession = Depends(get_db)):
    now = datetime.now(timezone.utc)

    task = Task(
        task_id=_generate_task_id(),
        status=TaskStatus.pending,
        task_type=body.task_type,
        payload=body.payload,
        priority=body.priority,
        max_retries=body.max_retries,
        retry_count=0,
        created_at=now,
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)

    process_task.delay(task.task_id)
    tasks_submitted_total.labels(task_type=task.task_type).inc()

    return _row_to_response(task)


@router.get(
    "/{task_id}",
    response_model=TaskResponse,
    dependencies=[Depends(rate_limit(limit=120, window_seconds=60))],
)
async def get_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
):
    # Check the cache first
    cached = await get_cached_task(redis, task_id)
    if cached is not None:
        return cached

    # Cache miss: read from the database
    stmt = select(Task).where(Task.task_id == task_id)
    result = await db.execute(stmt)
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    response = _row_to_response(task)
    await cache_task(redis, response)
    return response


@router.get(
    "",
    response_model=TaskListResponse,
    dependencies=[Depends(rate_limit(limit=60, window_seconds=60))],
)
async def list_tasks(
    status: TaskStatus | None = Query(default=None),
    priority: TaskPriority | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    query = select(Task)

    if status:
        query = query.where(Task.status == status)
    if priority:
        query = query.where(Task.priority == priority)

    query = query.order_by(Task.created_at.desc())

    count_stmt = select(func.count()).select_from(query.subquery())
    total_count = (await db.execute(count_stmt)).scalar_one()
    total_pages = max(1, (total_count + per_page - 1) // per_page)

    query = query.offset((page - 1) * per_page).limit(per_page)
    result = await db.execute(query)
    tasks = result.scalars().all()

    return TaskListResponse(
        tasks=[_row_to_response(t) for t in tasks],
        pagination=PaginationMeta(
            page=page,
            per_page=per_page,
            total_count=total_count,
            total_pages=total_pages,
        ),
    )


@router.delete("/{task_id}", response_model=TaskResponse)
async def cancel_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
):
    stmt = select(Task).where(Task.task_id == task_id)
    result = await db.execute(stmt)
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    if task.status != TaskStatus.pending:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot cancel task in '{task.status.value}' state. "
                   "Only pending tasks can be cancelled.",
        )

    task.status = TaskStatus.cancelled
    await db.commit()
    await db.refresh(task)

    # Invalidate the cache so subsequent reads see the new state
    await invalidate_task_cache(redis, task_id)

    return _row_to_response(task)