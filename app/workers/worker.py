"""
Worker
======
Worker يشتغل بـ asyncio:
- يستقبل مهام من Redis Queue
- ينفّذها (محاكاة بـ sleep)
- يبعت النتائج + Heartbeat + Leader Election
"""
import asyncio
import json
import time
import uuid
from typing import Optional
import redis.asyncio as aioredis

from app.workers.heartbeat import Heartbeat
from app.workers.election import LeaderElection


# القنوات والمفاتيح
TASKS_QUEUE = "tasks:queue"           # قائمة مهام (Redis List)
EVENTS_CHANNEL = "tasks:events"       # بث الأحداث


class Worker:
    """
    Worker واحد.
    
    - معرّف فريد (worker-xxxx)
    - يستقبل مهام من Redis List (BRPOP)
    - ينفّذها
    - يبعت النتائج
    """

    def __init__(self, redis: aioredis.Redis, worker_id: Optional[str] = None):
        self.redis = redis
        self.worker_id = worker_id or f"worker-{uuid.uuid4().hex[:6]}"
        self.heartbeat = Heartbeat(redis, self.worker_id)
        self.election = LeaderElection(redis, self.worker_id)
        self._running = False
        self.tasks_completed = 0
        self.tasks_failed = 0

    async def _publish_event(self, event_type: str, data: dict):
        """يبعت حدث على Redis Pub/Sub"""
        payload = {
            "event": event_type,
            "worker_id": self.worker_id,
            "timestamp": time.time(),
            **data,
        }
        await self.redis.publish(EVENTS_CHANNEL, json.dumps(payload))

    async def _execute_task(self, task: dict) -> bool:
        """
        ينفّذ مهمة (محاكاة بـ sleep حسب duration).
        يرجع True إذا نجح، False إذا فشل.
        """
        task_id = task.get("task_id", "unknown")
        duration = task.get("duration", 1.0)
        name = task.get("name", "unnamed")

        await self._publish_event("task_started", {
            "task_id": task_id,
            "task_name": name,
        })

        try:
            # محاكاة التنفيذ
            await asyncio.sleep(duration)

            await self._publish_event("task_completed", {
                "task_id": task_id,
                "task_name": name,
                "duration": duration,
            })
            self.tasks_completed += 1
            return True

        except Exception as e:
            await self._publish_event("task_failed", {
                "task_id": task_id,
                "task_name": name,
                "error": str(e),
            })
            self.tasks_failed += 1
            return False

    async def _task_loop(self):
        """حلقة استقبال المهام (blocking pop من Redis)"""
        print(f"[{self.worker_id}] Task loop started. Waiting for tasks...")
        while self._running:
            try:
                # BRPOP = blocking right pop (ينتظر 1 ثانية إذا القائمة فاضية)
                result = await self.redis.brpop(TASKS_QUEUE, timeout=1)
                if result is None:
                    continue

                _, raw = result
                try:
                    task = json.loads(raw)
                except json.JSONDecodeError:
                    print(f"[{self.worker_id}] Invalid task JSON: {raw}")
                    continue

                print(f"[{self.worker_id}] Executing task: {task.get('name')}")
                await self._execute_task(task)

            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"[{self.worker_id}] Task loop error: {e}")
                await asyncio.sleep(1)

    async def start(self):
        """يشغّل الـ Worker: heartbeat + election + task loop"""
        self._running = True
        print(f"[{self.worker_id}] Starting...")

        await self.heartbeat.start()
        await self.election.start()

        # بث إنه انضم
        await self._publish_event("worker_joined", {
            "worker_id": self.worker_id,
        })

        # الحلقة الرئيسية
        try:
            await self._task_loop()
        except asyncio.CancelledError:
            pass

    async def stop(self):
        """يوقف الـ Worker بشكل نظيف"""
        print(f"[{self.worker_id}] Stopping...")
        self._running = False

        await self.heartbeat.stop()
        await self.election.stop()

        # بث إنه خرج
        await self._publish_event("worker_left", {
            "worker_id": self.worker_id,
            "tasks_completed": self.tasks_completed,
            "tasks_failed": self.tasks_failed,
        })