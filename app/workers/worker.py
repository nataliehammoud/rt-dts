"""
Worker
======
Worker يشتغل بـ asyncio:
- يستقبل مهام من Redis Queue
- ينفّذها مع Retry Logic
- يبعت النتائج + Heartbeat + Leader Election
- المهام الفاشلة تروح لـ DLQ
- ✅ يحدّث DB: status + worker_id + started_at + finished_at
"""
import asyncio
import json
import time
import uuid
from datetime import datetime
from typing import Optional

import redis.asyncio as aioredis

from app.workers.heartbeat import Heartbeat
from app.workers.election import LeaderElection
from app.distributed.retry import RetryPolicy, retry_async, calculate_delay
from app.distributed.dlq import DeadLetterQueue
from app.db.session import SessionLocal
from app.db.models import Task, TaskStatus


# القنوات والمفاتيح
TASKS_QUEUE = "tasks:queue"
EVENTS_CHANNEL = "tasks:events"


class Worker:
    """
    Worker واحد.

    - معرّف فريد (worker-xxxx)
    - يستقبل مهام من Redis List (BRPOP)
    - ينفّذها مع Retry Logic
    - المهام الفاشلة تروح لـ DLQ
    - يحدّث حالة المهام في DB (running / completed / failed)
    """

    def __init__(
        self,
        redis: aioredis.Redis,
        worker_id: Optional[str] = None,
        retry_policy: Optional[RetryPolicy] = None,
    ):
        self.redis = redis
        self.worker_id = worker_id or f"worker-{uuid.uuid4().hex[:6]}"
        self.heartbeat = Heartbeat(redis, self.worker_id)
        self.election = LeaderElection(redis, self.worker_id)
        self.dlq = DeadLetterQueue(redis)
        self.retry_policy = retry_policy or RetryPolicy(
            max_attempts=3,
            base_delay=0.5,
            max_delay=5.0,
        )
        self._running = False
        self.tasks_completed = 0
        self.tasks_failed = 0
        self.tasks_retried = 0

    # ==================== Events ====================

    async def _publish_event(self, event_type: str, data: dict):
        """يبعت حدث على Redis Pub/Sub"""
        payload = {
            "event": event_type,
            "worker_id": self.worker_id,
            "timestamp": time.time(),
            **data,
        }
        await self.redis.publish(EVENTS_CHANNEL, json.dumps(payload))

    # ==================== DB Tracking ====================

    async def _mark_task_running(self, task_id: int):
        """يحدّث الحالة لـ running + worker_id + started_at"""

        def _do():
            db = SessionLocal()
            try:
                task = db.query(Task).filter(Task.id == task_id).first()
                if task:
                    task.status = TaskStatus.running.value
                    task.worker_id = self.worker_id
                    task.started_at = datetime.utcnow()
                    db.commit()
            except Exception as e:
                db.rollback()
                print(f"[{self.worker_id}] DB running update failed: {e}")
            finally:
                db.close()

        await asyncio.to_thread(_do)

    async def _mark_task_completed(self, task_id: int):
        """يحدّث الحالة لـ completed + finished_at"""

        def _do():
            db = SessionLocal()
            try:
                task = db.query(Task).filter(Task.id == task_id).first()
                if task:
                    task.status = TaskStatus.completed.value
                    task.finished_at = datetime.utcnow()
                    db.commit()
            except Exception as e:
                db.rollback()
                print(f"[{self.worker_id}] DB completed update failed: {e}")
            finally:
                db.close()

        await asyncio.to_thread(_do)

    async def _mark_task_failed(self, task_id: int):
        """يحدّث الحالة لـ failed + finished_at"""

        def _do():
            db = SessionLocal()
            try:
                task = db.query(Task).filter(Task.id == task_id).first()
                if task:
                    task.status = TaskStatus.failed.value
                    task.finished_at = datetime.utcnow()
                    db.commit()
            except Exception as e:
                db.rollback()
                print(f"[{self.worker_id}] DB failed update failed: {e}")
            finally:
                db.close()

        await asyncio.to_thread(_do)

    # ==================== Execution ====================

    async def _execute_task_once(self, task: dict) -> bool:
        """
        محاولة واحدة لتنفيذ المهمة.
        - لو `force_fail=True` → نرفع خطأ (للاختبار)
        - غير هيك → محاكاة بـ sleep
        """
        if task.get("force_fail"):
            raise RuntimeError(f"Simulated failure: {task.get('name')}")

        duration = task.get("duration", 1.0)
        await asyncio.sleep(duration)
        return True

    async def _execute_task(self, task: dict) -> bool:
        """
        ينفّذ مهمة مع Retry Logic.
        يرجع True إذا نجح، False إذا فشل نهائيًا.
        """
        task_id = task.get("task_id", "unknown")
        name = task.get("name", "unnamed")

        await self._publish_event("task_started", {
            "task_id": task_id,
            "task_name": name,
        })

        def on_retry(attempt: int, exc: Exception):
            self.tasks_retried += 1
            print(f"[{self.worker_id}] ⚠️  Retry {attempt}/{self.retry_policy.max_attempts} for {name}: {exc}")
            asyncio.create_task(self._publish_event("task_retry", {
                "task_id": task_id,
                "task_name": name,
                "attempt": attempt,
                "error": str(exc),
            }))

        try:
            await retry_async(
                func=lambda: self._execute_task_once(task),
                policy=self.retry_policy,
                on_retry=on_retry,
            )

            await self._publish_event("task_completed", {
                "task_id": task_id,
                "task_name": name,
            })
            self.tasks_completed += 1
            print(f"[{self.worker_id}] ✅ Task {name} completed")
            return True

        except Exception as e:
            # كل المحاولات فشلت → DLQ
            print(f"[{self.worker_id}] ❌ Task {name} FAILED after {self.retry_policy.max_attempts} attempts: {e}")
            await self.dlq.push(
                task=task,
                reason=str(e),
                attempts=self.retry_policy.max_attempts,
            )
            await self._publish_event("task_failed", {
                "task_id": task_id,
                "task_name": name,
                "error": str(e),
                "moved_to_dlq": True,
            })
            self.tasks_failed += 1
            return False

    # ==================== Loop ====================

    async def _task_loop(self):
        """حلقة استقبال المهام"""
        print(f"[{self.worker_id}] Task loop started. Waiting for tasks...")
        while self._running:
            try:
                result = await self.redis.brpop(TASKS_QUEUE, timeout=1)
                if result is None:
                    continue

                _, raw = result
                try:
                    task = json.loads(raw)
                except json.JSONDecodeError:
                    print(f"[{self.worker_id}] Invalid task JSON: {raw}")
                    continue

                # ✅ سجّلي إنك بديتي تنفذي المهمة
                task_id_raw = task.get("task_id")
                task_id_int: Optional[int] = None
                if task_id_raw is not None:
                    try:
                        task_id_int = int(task_id_raw)
                    except (ValueError, TypeError):
                        print(f"[{self.worker_id}] Invalid task_id in payload: {task_id_raw}")
                        task_id_int = None

                if task_id_int is not None:
                    await self._mark_task_running(task_id_int)

                print(f"[{self.worker_id}] 📥 Executing: {task.get('name')}")
                success = await self._execute_task(task)

                # ✅ سجّلي النتيجة
                if task_id_int is not None:
                    if success:
                        await self._mark_task_completed(task_id_int)
                    else:
                        await self._mark_task_failed(task_id_int)

            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"[{self.worker_id}] Task loop error: {e}")
                await asyncio.sleep(1)

    # ==================== Lifecycle ====================

    async def start(self):
        """يشغّل الـ Worker"""
        self._running = True
        print(f"[{self.worker_id}] Starting...")

        await self.heartbeat.start()
        await self.election.start()

        await self._publish_event("worker_joined", {
            "worker_id": self.worker_id,
        })

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

        await self._publish_event("worker_left", {
            "worker_id": self.worker_id,
            "tasks_completed": self.tasks_completed,
            "tasks_failed": self.tasks_failed,
            "tasks_retried": self.tasks_retried,
        })
