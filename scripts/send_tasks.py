"""
Send Test Tasks
===============
Send test tasks to Redis Queue.

Usage:
    python scripts/send_tasks.py [count]
"""
import asyncio
import json
import sys
import os

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.redis_client import redis_client
from app.workers.worker import TASKS_QUEUE


async def send_tasks(count: int = 5):
    """Send `count` tasks to queue"""
    for i in range(count):
        task = {
            "task_id": str(i),
            "name": f"task-{i}",
            "duration": 1.0,
        }
        await redis_client.lpush(TASKS_QUEUE, json.dumps(task))
        print(f"Sent: {task['name']}")

    await redis_client.aclose()
    print(f"Done. Sent {count} tasks.")


if __name__ == "__main__":
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    asyncio.run(send_tasks(count))