import pytest
from redis.asyncio import Redis as AsyncRedis

from src.app.services.cache import CACHE_KEY_PREFIX


@pytest.fixture
async def redis():
    """Fixture providing a Redis client for verification in tests."""
    client = AsyncRedis.from_url("redis://localhost:6379/1", decode_responses=True)
    yield client
    await client.aclose()


@pytest.mark.asyncio
async def test_get_task_populates_cache(client, redis):
    create_resp = await client.post(
        "/api/v1/tasks",
        json={"task_type": "cache_test"},
    )
    task_id = create_resp.json()["task_id"]

    await client.get(f"/api/v1/tasks/{task_id}")

    cached = await redis.get(f"{CACHE_KEY_PREFIX}{task_id}")
    assert cached is not None
    assert task_id in cached


@pytest.mark.asyncio
async def test_cancel_invalidates_cache(client, redis):
    from src.app.workers.celery_app import celery as celery_app

    celery_app.conf.update(task_always_eager=False)
    try:
        create_resp = await client.post(
            "/api/v1/tasks",
            json={"task_type": "cache_test"},
        )
        task_id = create_resp.json()["task_id"]

        # Populate cache
        await client.get(f"/api/v1/tasks/{task_id}")
        assert await redis.get(f"{CACHE_KEY_PREFIX}{task_id}") is not None

        await client.delete(f"/api/v1/tasks/{task_id}")
        assert await redis.get(f"{CACHE_KEY_PREFIX}{task_id}") is None
    finally:
        celery_app.conf.update(task_always_eager=True)