import pytest


@pytest.mark.asyncio
async def test_rate_limit_blocks_excessive_posts(client):
    """The POST endpoint allows 10 requests per 60 seconds."""
    # Send 10 valid requests
    for _ in range(10):
        resp = await client.post("/api/v1/tasks", json={"task_type": "rl_test"})
        assert resp.status_code == 202

    # The 11th should be rate limited
    resp = await client.post("/api/v1/tasks", json={"task_type": "rl_test"})
    assert resp.status_code == 429
    assert resp.headers.get("Retry-After") == "60"
    assert resp.headers.get("X-RateLimit-Limit") == "10"


@pytest.mark.asyncio
async def test_rate_limit_isolated_per_endpoint(client):
    """Hitting the POST limit should not affect GET."""
    for _ in range(10):
        await client.post("/api/v1/tasks", json={"task_type": "isolation_test"})

    resp = await client.post("/api/v1/tasks", json={"task_type": "isolation_test"})
    assert resp.status_code == 429

    # GET should still work because it has its own quota
    resp = await client.get("/api/v1/tasks")
    assert resp.status_code == 200