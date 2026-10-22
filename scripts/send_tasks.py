"""
Send Tasks Script
=================
ينشئ N مهمة في DB + يرسلها لـ Redis Queue.
استخدام: python scripts/send_tasks.py 5
"""
import asyncio
import json
import sys
from pathlib import Path

# ✅ FIX: أضيفي جذر المشروع للـ sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.redis_client import redis_client, close_redis
from app.db.session import SessionLocal
from app.db.models import Task, TaskStatus


TASKS_QUEUE = "tasks:queue"


async def send_tasks(n: int) -> int:
    db = SessionLocal()
    sent = 0
    try:
        for i in range(n):
            # 1) إنشاء المهمة في DB
            task = Task(
                name=f"task-{i}",
                duration=2.0,
                status=TaskStatus.pending.value,  # ← lowercase
            )
            db.add(task)
            db.commit()
            db.refresh(task)  # ← يجيب الـ id بعد commit

            # 2) دفعها لـ Redis مع DB id الحقيقي
            payload = {
                "task_id": task.id,  # ← DB id، مو local counter
                "name": task.name,
                "duration": task.duration,
                "force_fail": False,
            }
            await redis_client.lpush(TASKS_QUEUE, json.dumps(payload))
            print(f"Sent: {task.name} (id={task.id})")
            sent += 1
    finally:
        db.close()
    return sent


async def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    sent = await send_tasks(n)
    print(f"Done. Sent {sent} tasks.")
    await close_redis()


if __name__ == "__main__":
    asyncio.run(main())