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
    assert data["status"] == "pending"
    assert data["task_id"].startswith("tsk_")
    assert data["task_type"] == "image_resize"


@pytest.mark.asyncio
async def test_get_task(client):
    # First create a task
    create_resp = await client.post(
        "/api/v1/tasks",
        json={"task_type": "test_job"},
    )
    task_id = create_resp.json()["task_id"]

    # Then retrieve it
    get_resp = await client.get(f"/api/v1/tasks/{task_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["task_id"] == task_id


@pytest.mark.asyncio
async def test_get_nonexistent_task(client):
    response = await client.get("/api/v1/tasks/tsk_doesnotexist")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_cancel_pending_task(client):
    create_resp = await client.post(
        "/api/v1/tasks",
        json={"task_type": "test_job"},
    )
    task_id = create_resp.json()["task_id"]

    cancel_resp = await client.delete(f"/api/v1/tasks/{task_id}")
    assert cancel_resp.status_code == 200
    assert cancel_resp.json()["status"] == "cancelled"


@pytest.mark.asyncio
async def test_cancel_already_cancelled_task(client):
    create_resp = await client.post(
        "/api/v1/tasks",
        json={"task_type": "test_job"},
    )
    task_id = create_resp.json()["task_id"]

    await client.delete(f"/api/v1/tasks/{task_id}")
    second_cancel = await client.delete(f"/api/v1/tasks/{task_id}")
    assert second_cancel.status_code == 409


@pytest.mark.asyncio
async def test_list_tasks_pagination(client):
    # Create 3 tasks
    for i in range(3):
        await client.post("/api/v1/tasks", json={"task_type": f"job_{i}"})

    response = await client.get("/api/v1/tasks?per_page=2&page=1")
    data = response.json()
    assert len(data["tasks"]) == 2
    assert data["pagination"]["total_count"] >= 3
    assert data["pagination"]["total_pages"] >= 2


@pytest.mark.asyncio
async def test_list_tasks_filter_by_status(client):
    create_resp = await client.post(
        "/api/v1/tasks",
        json={"task_type": "to_cancel"},
    )
    task_id = create_resp.json()["task_id"]
    await client.delete(f"/api/v1/tasks/{task_id}")

    response = await client.get("/api/v1/tasks?status=cancelled")
    data = response.json()
    cancelled_ids = [t["task_id"] for t in data["tasks"]]
    assert task_id in cancelled_ids


@pytest.mark.asyncio
async def test_health_check(client):
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"