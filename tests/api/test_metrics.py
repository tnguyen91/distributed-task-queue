import pytest


@pytest.mark.asyncio
async def test_metrics_endpoint_exposed(client):
    response = await client.get("/metrics")
    assert response.status_code == 200
    body = response.text
    assert "starlette_requests_total" in body or "starlette_request_count" in body


@pytest.mark.asyncio
async def test_task_submission_increments_counter(client):
    await client.post("/api/v1/tasks", json={"task_type": "metric_test"})

    response = await client.get("/metrics")
    assert response.status_code == 200
    assert "tasks_submitted_total" in response.text
    assert 'task_type="metric_test"' in response.text