"""
Send Failing Task
=================
Send a task that will fail (force_fail=True).

Usage:
    python scripts/send_failing_task.py
"""
import asyncio
import json
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.redis_client import redis_client
from app.workers.worker import TASKS_QUEUE


async def send_failing():
    task = {
        "task_id": "fail-1",
        "name": "failing-task",
        "duration": 1.0,
        "force_fail": True,
    }
    await redis_client.lpush(TASKS_QUEUE, json.dumps(task))
    print(f"Sent failing task: {task['name']}")
    await redis_client.aclose()


if __name__ == "__main__":
    asyncio.run(send_failing())