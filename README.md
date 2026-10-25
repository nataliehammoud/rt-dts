# RT-DTS: Real-Time Distributed Task Scheduler

A distributed task scheduling system built with FastAPI, Redis, MySQL, and React. Implements real-time scheduling algorithms (RM and EDF), distributed worker coordination with leader election, fault tolerance via retry and dead letter queues, and an analytics data warehouse.

## Overview

RT-DTS demonstrates how a distributed system handles real-time task scheduling with independent workers, leader election, and observable analytics. The system is built around three principles:

- Independent failure: workers run as separate containers and can fail without stopping the system
- Correct coordination: leader election uses Redis SETNX with safe TTL renewal
- Accurate data: analytics come from real task executions, not placeholders

## Architecture

```text
                    +-----------------+
                    |  React Dashboard|
                    +--------+--------+
                             |
                          WebSocket
                             |
                    +--------v--------+
                    |   FastAPI API   |
                    +--------+--------+
                             |
          +------------------+------------------+
          |                  |                  |
    +-----v-----+      +-----v-----+      +-----v------+
    |   MySQL   |      |   Redis   |      | Warehouse  |
    |  (OLTP)   |      |  (Queue)  |      |(Star Schema)|
    +-----------+      +-----+-----+      +------------+
                             |
             +---------------+---------------+ 
             |               |               |
       +-----v-----+   +-----v-----+   +-----v-----+
       | Worker 1  |   | Worker 2  |   | Worker 3  |
       +-----------+   +-----------+   +-----------+
             |               |               |
             +---------------+---------------+ 
                    Leader Election
```

## Quick Start

### Prerequisites

- Docker Desktop (with WSL 2 on Windows)
- Node.js 20 or newer
- 4 GB RAM minimum

### Steps

1. Clone the repository:

```bash
git clone https://github.com/nataliehammoud/rt-dts.git
cd rt-dts
```

2. Configure environment:

```bash
cp .env.example .env
```

3. Start the backend stack:

```bash
docker compose up -d --build
```

This starts six containers: MySQL, Redis, the API, and three independent workers.

4. Start the frontend:

```bash
cd frontend
npm install
npm run dev
```

5. Open in browser:

| Service | URL |
|---------|-----|
| Dashboard | http://localhost:3000 |
| API Docs | http://localhost:8000/docs |
| Health Check | http://localhost:8000/health |

6. Send test tasks:

```bash
docker compose exec api python scripts/send_tasks.py 5
```

## Key Technical Decisions

### Real Distributed Workers

Each worker runs as an independent Docker container with its own process. The workers depend on MySQL and Redis, but not on the API container. This means the API can restart or fail without affecting task processing.

Proof: stopping the API container leaves all workers running. Stopping the leader worker triggers a new leader election within ten seconds.

### Leader Election with Safe TTL Renewal

A common bug in Redis-based leader election is that every worker renews the TTL, not just the leader. This causes race conditions and potential split-brain scenarios.

The fix verifies identity before renewing:

```python
async def _renew(self):
    current = await self.redis.get(LEADER_KEY)
    if current and as_string(current) == self.worker_id:
        await self.redis.expire(LEADER_KEY, LEADER_TTL)
        return True
    return False
```

Only the current leader renews its lease. Other workers attempt to acquire the lock. No overlap occurs.

### Scheduling Algorithms

Rate Monotonic (RM) and Earliest Deadline First (EDF) are implemented from scratch. RM uses the Liu and Layland bound for sufficient schedulability, while Response Time Analysis provides the exact test. EDF uses the utilization bound.

Source code is in `app/scheduler/`. Fourteen unit tests cover the algorithms.

### Accurate ETL Pipeline

Workers write `worker_id`, `started_at`, and `finished_at` to the tasks table during execution. The ETL job reads these values every sixty seconds and loads them into a star schema:

```text
dim_task     +
dim_worker   |
dim_status   +--> fact_task_execution
dim_time     +
```

Every fact row reflects a real task execution by a real worker.

## API Reference

### Tasks

| Method | Path | Description |
|--------|------|-------------|
| POST | /tasks/ | Create a task |
| GET | /tasks/ | List all tasks |
| GET | /tasks/{id} | Get a single task |

### Scheduler

| Method | Path | Description |
|--------|------|-------------|
| POST | /scheduler/analyze | Analyze a task set with RM and EDF |
| POST | /scheduler/simulate/rm | Simulate Rate Monotonic |
| POST | /scheduler/simulate/edf | Simulate Earliest Deadline First |

### Analytics

| Method | Path | Description |
|--------|------|-------------|
| GET | /analytics/summary | Overall KPIs |
| GET | /analytics/workers | Per-worker statistics |
| GET | /analytics/tasks | Task statistics |
| GET | /analytics/timeline | Time-series evolution |

### System

| Method | Path | Description |
|--------|------|-------------|
| GET | /health | Health check |
| WS | /ws/events | Live event stream |

## Testing

Run the test suite:

```bash
docker compose exec api pytest tests/ -v
```

Expected result: twenty-five passing tests.

Coverage includes:

- RM and EDF schedulability bounds
- Response Time Analysis
- Consistent hashing ring
- Retry with exponential backoff
- Dead Letter Queue behavior

## Data Warehouse

The ETL job runs every sixty seconds. Example output from the analytics endpoint:

```json
[
  {"worker_id": "worker-1", "total_tasks": 3, "completed": 3, "success_rate": 100.0},
  {"worker_id": "worker-2", "total_tasks": 3, "completed": 3, "success_rate": 100.0},
  {"worker_id": "worker-3", "total_tasks": 7, "completed": 7, "success_rate": 100.0}
]
```

All numbers come from real worker activity.

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | FastAPI, Python 3.12, Pydantic v2 |
| OLTP Database | MySQL 8.0 |
| OLAP Database | Same MySQL instance, star schema |
| Cache and Queue | Redis 7 (Lists, Pub/Sub, SETNX) |
| Workers | Python asyncio with aioredis |
| Frontend | React 19, TypeScript, Tailwind v4, Recharts |
| Real-time | WebSocket with Redis Pub/Sub bridge |
| Containerization | Docker and Docker Compose |
| Testing | pytest and httpx |

## Project Structure

```text
rt-dts/
  app/
    api/           REST endpoints
    core/          Settings and Redis client
    db/            SQLAlchemy models (OLTP)
    scheduler/     RM, EDF, RTA algorithms
    workers/       Worker, heartbeat, leader election
    distributed/   Hash ring, retry policy, dead letter queue
    warehouse/     Star schema and ETL job
    ws/            WebSocket manager and bridge
  frontend/        React dashboard
  scripts/         Test scripts and utilities
  tests/           25 pytest tests
  docker-compose.yml
  .env.example
```

## What I Learned

- Distributed systems are defined by independent failure, not by internet scale
- Leader election requires careful TTL handling to avoid split-brain
- Enum to database string conversion needs `.value`, otherwise silent bugs occur
- SQLAlchemy accepts dynamic attributes without a Column, but they do not persist
- Docker build context matters: reducing from 160 MB to 1.2 MB made builds fifteen times faster

## Known Limitations

This is a portfolio project, not production software. The following limitations are intentional and documented:

- No authentication: all endpoints are open
- No HTTPS: HTTP only for local development
- No rate limiting: the API could be flooded
- Weak default passwords in the example environment file
- No CI/CD pipeline: tests run manually
- No monitoring integration
- Single-host deployment: designed for Docker Desktop on one machine

Each limitation is a clear next step for a future iteration.

## Author

Natalie Hammoud

GitHub: https://github.com/nataliehammoud

## License

MIT