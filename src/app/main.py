from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.app.api import health, tasks
from src.app.core.config import settings
from src.app.core.redis_client import redis_client

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await redis_client.aclose()


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.include_router(health.router)
app.include_router(tasks.router)