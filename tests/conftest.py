import pytest
from typing import AsyncGenerator
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from redis import Redis as SyncRedis
from redis.asyncio import Redis as AsyncRedis

import src.app.workers.task_handlers as _task_handlers
from src.app.core.deps import get_db
from src.app.main import app
from src.app.models.base import Base
from src.app.workers.celery_app import celery as celery_app
from src.app.core.redis_client import get_redis

celery_app.conf.update(task_always_eager=True, task_eager_propagates=True)

TEST_DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5433/taskqueue_test"
TEST_SYNC_DATABASE_URL = "postgresql+psycopg2://postgres:postgres@localhost:5433/taskqueue_test"
TEST_REDIS_URL = "redis://localhost:6379/1"

engine_test = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)
async_session_test = async_sessionmaker(engine_test, expire_on_commit=False)

# Redirect the Celery worker's sync session to the test database
_sync_engine_test = create_engine(TEST_SYNC_DATABASE_URL, poolclass=NullPool)
_task_handlers.SyncSession = sessionmaker(_sync_engine_test)


async def override_get_db():
    async with async_session_test() as session:
        yield session


async def override_get_redis() -> AsyncGenerator[AsyncRedis, None]:
    redis = AsyncRedis.from_url(TEST_REDIS_URL, decode_responses=True)
    yield redis
    await redis.aclose()


app.dependency_overrides[get_db] = override_get_db
app.dependency_overrides[get_redis] = override_get_redis

# Point the Celery worker's sync Redis to the test database
_task_handlers.sync_redis = SyncRedis.from_url(TEST_REDIS_URL, decode_responses=True)


@pytest.fixture(autouse=True)
async def setup_db():
    async with engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture(autouse=True)
async def clear_redis():
    redis = AsyncRedis.from_url(TEST_REDIS_URL, decode_responses=True)
    await redis.flushdb()
    yield
    await redis.aclose()