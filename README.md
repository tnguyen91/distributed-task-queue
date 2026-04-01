# Distributed Task Queue

A distributed task queue with real-time monitoring, built with FastAPI, PostgreSQL, Redis, and Celery.

## Architecture

```
┌─────────┐       ┌──────────────────┐
│  Client  │──────▶│  FastAPI Server   │
└─────────┘ HTTP  │  (validates,      │
                   │   routes, caches) │
                   └──┬──────┬────────┘
                      │      │
              ┌───────▼──┐ ┌─▼───────────┐
              │PostgreSQL │ │    Redis     │
              │(durable   │ │(broker +    │
              │ storage)  │ │ cache)      │
              └───────▲──┘ └─┬───────────┘
                      │      │
                   ┌──┴──────▼────────┐
                   │  Celery Workers   │
                   │  (execute tasks,  │
                   │   store results)  │
                   └──────────────────┘
```

- **FastAPI** — validates input, persists task metadata to PostgreSQL, enqueues to Redis, returns immediately. P95 target: <200ms.
- **PostgreSQL** — source of truth. ACID transactions, complex filtering/pagination via SQL.
- **Redis** — dual role: Celery message broker and read-through cache for status lookups.
- **Celery Workers** — pull tasks from Redis, execute, write results to PostgreSQL. Scale horizontally.

### Design decisions

| Decision | Choice | Tradeoff |
|----------|--------|----------|
| Delivery semantics | At-least-once | Tasks may run twice on worker crash, but never lost. Exactly-once requires distributed transactions or idempotency keys. |
| API response | Async (202) | Client doesn't wait. API stays fast under heavy load. |
| Broker | Redis | Simpler than RabbitMQ/Kafka at ~500 tasks/min. Would revisit at ~50K+. |
| Datastore | PostgreSQL | ACID + SQL queries. Redis alone risks data loss and can't filter efficiently. |
| Caching | Redis + TTL | Offloads repeat status reads from Postgres. Stale by up to TTL seconds. |

## Requirements

**Functional**
- Submit tasks with type, payload, and priority
- Track status: pending → running → completed/failed
- Retrieve results, list with filtering/pagination, cancel pending tasks

**Non-functional**
- Throughput: ~500 tasks/min
- API latency: <200ms P95
- At-least-once delivery, tasks survive restarts, horizontal scaling

## API

| Method | Path | Description | Status |
|--------|------|-------------|--------|
| POST | /api/v1/tasks | Submit a task | 202 |
| GET | /api/v1/tasks/{id} | Get status + result | 200 |
| GET | /api/v1/tasks | List tasks (filterable, paginated) | 200 |
| DELETE | /api/v1/tasks/{id} | Cancel a pending task | 200/409 |
| GET | /api/v1/health | Health check | 200 |

## Stack

| Layer | Tool |
|-------|------|
| Framework | FastAPI |
| Database | PostgreSQL |
| Cache/Broker | Redis |
| Task queue | Celery |
| Containers | Docker Compose |
| CI/CD | GitHub Actions |
| Testing | pytest + httpx |

## Quick start

```bash
git clone https://github.com/YOUR_USERNAME/distributed-task-queue.git
cd distributed-task-queue
pip install -r requirements.txt
uvicorn src.app.main:app --reload
# Docs: http://localhost:8000/docs
```

## Project structure

```
src/app/
├── api/          # Route handlers
├── core/         # Config, database, security
├── models/       # SQLAlchemy models
├── schemas/      # Pydantic schemas
├── services/     # Business logic
└── workers/      # Celery tasks
tests/
├── api/
├── services/
└── workers/
```
