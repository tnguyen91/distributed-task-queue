import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

import src.app.workers.task_handlers as _task_handlers
from src.app.core.deps import get_db
from src.app.main import app
from src.app.models.base import Base
from src.app.workers.celery_app import celery as celery_app

celery_app.conf.update(task_always_eager=True, task_eager_propagates=True)

TEST_DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5433/taskqueue_test"
TEST_SYNC_DATABASE_URL = "postgresql+psycopg2://postgres:postgres@localhost:5433/taskqueue_test"

engine_test = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)
async_session_test = async_sessionmaker(engine_test, expire_on_commit=False)

# Redirect the Celery worker's sync session to the test database
_sync_engine_test = create_engine(TEST_SYNC_DATABASE_URL, poolclass=NullPool)
_task_handlers.SyncSession = sessionmaker(_sync_engine_test)


async def override_get_db():
    async with async_session_test() as session:
        yield session


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
async def setup_db():
    async with engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c