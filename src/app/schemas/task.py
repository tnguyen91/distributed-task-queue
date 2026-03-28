from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


class TaskPriority(str, Enum):
    low = "low"
    normal = "normal"
    high = "high"


class TaskCreate(BaseModel):
    """What the client sends when submitting a new task."""
    task_type: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="The kind of task to execute",
        json_schema_extra={"example": "image_resize"},
    )
    payload: dict[str, Any] = Field(
        default_factory=dict,
        description="Task-specific input data",
    )
    priority: TaskPriority = TaskPriority.normal
    max_retries: int = Field(default=3, ge=0, le=10)


class TaskResponse(BaseModel):
    """What the API returns for a single task."""
    task_id: str
    status: TaskStatus
    task_type: str
    payload: dict[str, Any]
    result: dict[str, Any] | None = None
    error_message: str | None = None
    priority: TaskPriority
    max_retries: int
    retry_count: int = 0
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None


class TaskListResponse(BaseModel):
    """Paginated list of tasks."""
    tasks: list[TaskResponse]
    pagination: "PaginationMeta"


class PaginationMeta(BaseModel):
    page: int
    per_page: int
    total_count: int
    total_pages: int


TaskListResponse.model_rebuild()