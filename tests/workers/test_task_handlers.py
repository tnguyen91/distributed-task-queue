import pytest

import src.app.workers.task_handlers as _task_handlers
from src.app.models.task import Task
from src.app.schemas.task import TaskStatus
from src.app.workers.celery_app import celery as celery_app
from src.app.workers.task_handlers import process_task


def _create_task(task_id: str, max_retries: int) -> None:
    with _task_handlers.SyncSession() as session:
        session.add(Task(
            task_id=task_id,
            status=TaskStatus.pending,
            task_type="test_job",
            payload={"key": "value"},
            max_retries=max_retries,
            retry_count=0,
        ))
        session.commit()


def _get_task(task_id: str) -> Task:
    with _task_handlers.SyncSession() as session:
        return session.query(Task).filter_by(task_id=task_id).one()


@pytest.fixture
def failing_execute(monkeypatch):
    calls = []

    def _raise(task_type, payload):
        calls.append(task_type)
        raise RuntimeError("boom")

    monkeypatch.setattr(_task_handlers, "_execute_task", _raise)
    return calls


@pytest.mark.asyncio
async def test_task_fails_permanently_when_retries_exhausted(failing_execute):
    _create_task("tsk_fail_once", max_retries=1)

    process_task.apply(args=["tsk_fail_once"])

    task = _get_task("tsk_fail_once")
    assert failing_execute == ["test_job"]
    assert task.status == TaskStatus.failed
    assert task.error_message == "boom"
    assert task.retry_count == 1
    assert task.completed_at is not None


@pytest.mark.asyncio
async def test_task_retries_until_max_retries(failing_execute, monkeypatch):
    _create_task("tsk_fail_retry", max_retries=3)

    # With propagation off, apply() runs each retry synchronously (ignoring
    # backoff) instead of raising celery.exceptions.Retry back to the caller
    monkeypatch.setattr(celery_app.conf, "task_eager_propagates", False)
    process_task.apply(args=["tsk_fail_retry"])

    task = _get_task("tsk_fail_retry")
    assert len(failing_execute) == 3
    assert task.status == TaskStatus.failed
    assert task.retry_count == 3
