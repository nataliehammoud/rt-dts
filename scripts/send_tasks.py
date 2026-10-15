"""
Send Test Tasks
===============
يرسل مهام تجريبية إلى Redis Queue.

الاستخدام:
    python scripts/send_tasks.py [count]
"""
import asyncio
import json
import sys
from app.core.redis_client import redis_client
from app.workers.worker import TASKS_QUEUE


async def send_tasks(count: int = 5):
    """يرسل `count` مهمة إلى Queue"""
    for i in range(count):
        task = {
            "task_id": str(i),
            "name": f"task-{i}",
            "duration": 1.0,
        }
        await redis_client.lpush(TASKS_QUEUE, json.dumps(task))
        print(f"📤 Sent: {task['name']}")

    # إغلاق الاتصال بشكل نظيف
    await redis_client.aclose()
    print(f"✅ Sent {count} tasks.")


if __name__ == "__main__":
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    asyncio.run(send_tasks(count))