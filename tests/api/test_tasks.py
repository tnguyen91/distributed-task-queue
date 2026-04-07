import pytest

@pytest.mark.asyncio
async def test_submit_task(client):
    response = await client.post(
        "/api/v1/tasks",
        json={
            "task_type": "image_resize",
            "payload": {"width": 800},
            "priority": "normal",
            "max_retries": 3,
        },
    )
    assert response.status_code == 202
    data = response.json()
    assert data["task_id"].startswith("tsk_")
    assert data["task_type"] == "image_resize"
    assert data["status"] == "pending"


@pytest.mark.asyncio
async def test_task_gets_processed(client):
    create_resp = await client.post(
        "/api/v1/tasks",
        json={"task_type": "test_job", "payload": {"key": "value"}},
    )
    task_id = create_resp.json()["task_id"]

    get_resp = await client.get(f"/api/v1/tasks/{task_id}")
    assert get_resp.status_code == 200

    data = get_resp.json()
    assert data["status"] == "completed"
    assert data["result"] is not None
    assert data["started_at"] is not None
    assert data["completed_at"] is not None


@pytest.mark.asyncio
async def test_get_nonexistent_task(client):
    response = await client.get("/api/v1/tasks/tsk_doesnotexist")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_cancel_pending_task(client):
    from src.app.workers.celery_app import celery as celery_app

    celery_app.conf.update(task_always_eager=False)

    create_resp = await client.post(
        "/api/v1/tasks",
        json={"task_type": "test_job"},
    )
    task_id = create_resp.json()["task_id"]

    cancel_resp = await client.delete(f"/api/v1/tasks/{task_id}")
    assert cancel_resp.status_code == 200
    assert cancel_resp.json()["status"] == "cancelled"

    # Re-enable eager mode for remaining tests
    celery_app.conf.update(task_always_eager=True)


@pytest.mark.asyncio
async def test_cancel_completed_task(client):
    create_resp = await client.post(
        "/api/v1/tasks",
        json={"task_type": "test_job"},
    )
    task_id = create_resp.json()["task_id"]

    cancel_resp = await client.delete(f"/api/v1/tasks/{task_id}")
    assert cancel_resp.status_code == 409


@pytest.mark.asyncio
async def test_list_tasks_pagination(client):
    for i in range(3):
        await client.post("/api/v1/tasks", json={"task_type": f"job_{i}"})

    response = await client.get("/api/v1/tasks?per_page=2&page=1")
    data = response.json()
    assert len(data["tasks"]) == 2
    assert data["pagination"]["total_count"] >= 3
    assert data["pagination"]["total_pages"] >= 2


@pytest.mark.asyncio
async def test_list_tasks_filter_by_status(client):
    await client.post("/api/v1/tasks", json={"task_type": "job_a"})

    response = await client.get("/api/v1/tasks?status=completed")
    data = response.json()
    assert len(data["tasks"]) >= 1
    assert all(t["status"] == "completed" for t in data["tasks"])


@pytest.mark.asyncio
async def test_health_check(client):
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"