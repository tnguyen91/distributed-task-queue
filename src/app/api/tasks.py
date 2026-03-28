import secrets
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query

from src.app.schemas.task import (
    TaskCreate,
    TaskListResponse,
    TaskPriority,
    TaskResponse,
    TaskStatus,
    PaginationMeta,
)

router = APIRouter(prefix="/api/v1/tasks", tags=["tasks"])

_tasks: dict[str, dict] = {}


def _generate_task_id() -> str:
    return f"tsk_{secrets.token_hex(8)}"


@router.post("", status_code=202, response_model=TaskResponse)
async def submit_task(body: TaskCreate):
    """Submit a new task for async processing."""
    task_id = _generate_task_id()
    now = datetime.now(timezone.utc)

    task = {
        "task_id": task_id,
        "status": TaskStatus.pending,
        "task_type": body.task_type,
        "payload": body.payload,
        "result": None,
        "error_message": None,
        "priority": body.priority,
        "max_retries": body.max_retries,
        "retry_count": 0,
        "created_at": now,
        "started_at": None,
        "completed_at": None,
    }
    _tasks[task_id] = task
    return task


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(task_id: str):
    """Get the current status and result of a task."""
    task = _tasks.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    return task


@router.get("", response_model=TaskListResponse)
async def list_tasks(
    status: TaskStatus | None = Query(default=None),
    priority: TaskPriority | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
):
    """List tasks with optional filtering and pagination."""
    filtered = list(_tasks.values())

    if status:
        filtered = [t for t in filtered if t["status"] == status]
    if priority:
        filtered = [t for t in filtered if t["priority"] == priority]

    # Sort newest first
    filtered.sort(key=lambda t: t["created_at"], reverse=True)

    total_count = len(filtered)
    total_pages = max(1, (total_count + per_page - 1) // per_page)

    start = (page - 1) * per_page
    page_items = filtered[start : start + per_page]

    return TaskListResponse(
        tasks=page_items,
        pagination=PaginationMeta(
            page=page,
            per_page=per_page,
            total_count=total_count,
            total_pages=total_pages,
        ),
    )


@router.delete("/{task_id}", response_model=TaskResponse)
async def cancel_task(task_id: str):
    """Cancel a pending task. Returns 409 if the task is already running or finished."""
    task = _tasks.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    if task["status"] != TaskStatus.pending:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot cancel task in '{task['status'].value}' state. Only pending tasks can be cancelled.",
        )

    task["status"] = TaskStatus.cancelled
    return task