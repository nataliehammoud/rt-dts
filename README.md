# RT-DTS: Real-Time Distributed Task Scheduler

A distributed task scheduling system built with FastAPI, Redis, MySQL, and React. Implements real-time scheduling algorithms (RM and EDF), distributed worker coordination with leader election, fault tolerance via retry and dead letter queues, an analytics data warehouse, and machine learning for duration prediction and anomaly detection.

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

### Leader Election with Atomic TTL Renewal

A common bug in Redis-based leader election is that every worker renews the TTL, not just the leader. This causes race conditions and potential split-brain scenarios.

The fix uses a Lua script that atomically checks ownership and renews in a single operation:

```python
RENEW_SCRIPT = """
if redis.call("GET", KEYS[1]) == ARGV[1] then
    return redis.call("EXPIRE", KEYS[1], ARGV[2])
else
    return 0
end
"""

async def _renew(self):
    result = await self.redis.eval(
        RENEW_SCRIPT, 1, LEADER_KEY, self.worker_id, LEADER_TTL
    )
    return int(result) == 1
```

Only the current leader renews its lease, and the operation is atomic. Release uses a similar script so a stale leader cannot delete someone else's lock.

### Stuck Task Cleanup

If a worker crashes after marking a task as `running`, the task would otherwise stay in that state forever. A background job runs every sixty seconds and moves any task that has been `running` for more than five minutes to `failed` with a `finished_at` timestamp. The API exposes this as a coroutine started alongside the ETL worker.

### Scheduling Algorithms

Rate Monotonic (RM) and Earliest Deadline First (EDF) are implemented from scratch. RM uses the Liu and Layland bound for sufficient schedulability, while Response Time Analysis provides the exact test. EDF uses the utilization bound.

Source code is in `app/scheduler/`. Fourteen unit tests cover the algorithms.

### Accurate ETL Pipeline

Workers write `worker_id`, `started_at`, and `finished_at` to the tasks table during execution. The ETL job reads these values every thirty seconds and loads them into a star schema:

```text
dim_task     +
dim_worker   |
dim_status   +--> fact_task_execution
dim_time     +
```

Every fact row reflects a real task execution by a real worker.

### AI Layer

Two machine learning models analyze task behavior:

- **Duration Predictor** (Linear Regression): predicts execution time based on task duration and period
- **Anomaly Detector** (Isolation Forest + business rules): flags workers with failure rate ≥ 50% or unusually long execution times

Models train on-demand via `POST /ml/train-models` and are cached in memory after first load. Trained model files (`*.joblib`) are gitignored and regenerated automatically when missing.

The anomaly detector combines ML with hard business rules because Isolation Forest requires diverse training data (some workers must already be anomalous to learn what "anomaly" looks like). With a homogeneous dataset of three healthy workers, the rules guarantee detection of obvious cases; the ML layer adds pattern recognition as more diverse data accumulates.

### Structured JSON Logging

All services use the Python standard `logging` module with a custom JSON formatter. Each log line is a JSON object with `timestamp`, `level`, `logger`, and `message` fields. This makes logs greppable, machine-parseable, and ready for ingestion into any log aggregator without extra configuration.

Example:

```json
{"timestamp":"2026-10-26T09:42:58.679011+00:00","level":"INFO","logger":"app.warehouse.etl","message":"etl_run scanned=62 inserted=0 skipped=62"}
```

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

### AI

| Method | Path | Description |
|--------|------|-------------|
| POST | /ml/predict-duration | Predict task execution time |
| POST | /ml/detect-anomaly | Detect anomalous worker behavior |
| POST | /ml/train-models | Retrain models on latest data |
| GET | /ml/model-stats | Check model availability |

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

The ETL job runs every thirty seconds. Example output from the analytics endpoint:

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
| Cache and Queue | Redis 7 (Lists, Pub/Sub, SETNX, Lua) |
| Workers | Python asyncio with aioredis |
| Frontend | React 19, TypeScript, Tailwind v4, Recharts |
| Real-time | WebSocket with Redis Pub/Sub bridge |
| ML | scikit-learn, joblib |
| Logging | Python logging with custom JSON formatter |
| Containerization | Docker and Docker Compose |
| Testing | pytest and httpx |

## Project Structure

```text
rt-dts/
  app/
    api/           REST endpoints (tasks, scheduler, analytics, ml)
    core/          Settings, Redis client, JSON logging
    db/            SQLAlchemy models (OLTP)
    scheduler/     RM, EDF, RTA algorithms
    workers/       Worker, heartbeat, leader election, cleanup
    distributed/   Hash ring, retry policy, dead letter queue
    warehouse/     Star schema and ETL job
    ml/            Duration predictor, anomaly detector
    ws/            WebSocket manager and bridge
  frontend/        React dashboard
  scripts/         Test scripts and utilities
  tests/           25 pytest tests
  docker-compose.yml
  .env.example
```

## What I Learned

- Distributed systems are defined by independent failure, not by internet scale
- Leader election requires atomic TTL handling to avoid split-brain; a Lua script beats a GET-then-EXPIRE sequence
- Enum to database string conversion needs `.value`, otherwise silent bugs occur
- SQLAlchemy accepts dynamic attributes without a Column, but they do not persist
- Docker build context matters: reducing from 160 MB to 1.2 MB made builds fifteen times faster
- Logging configuration must be set up in every process entry point, not just the main app
- Machine learning needs diverse training data; business rules are a reliable safety net when the dataset is small

## Known Limitations

This is a portfolio project, not production software. The following limitations are intentional and documented:

- No authentication: all endpoints are open
- No HTTPS: HTTP only for local development
- No rate limiting: the API could be flooded
- Weak default passwords in the example environment file
- No CI/CD pipeline: tests run manually
- No monitoring integration
- Single-host deployment: designed for Docker Desktop on one machine
- ML models train on limited data (three workers, uniform duration); business rules do the heavy lifting for anomaly detection
- Scheduler algorithms (RM/EDF) are exposed as endpoints but not yet used by the worker loop, which currently uses FIFO via Redis lists
- Consistent hash ring exists but is not yet wired into worker dispatch

Each limitation is a clear next step for a future iteration.

## Author

Natalie Hammoud

GitHub: https://github.com/nataliehammoud

## License

MIT