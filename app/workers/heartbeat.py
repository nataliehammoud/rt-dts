"""
Worker Heartbeat
================
كل Worker يبعت نبضة كل ثانية عشان يثبت إنه حي
"""
import asyncio
import json
import time
from typing import Optional
import redis.asyncio as aioredis


HEARTBEAT_INTERVAL = 1.0      # ثانية
HEARTBEAT_TTL = 5             # ثواني — إذا ما وصلت نبضة خلال 5 ثواني، نعتبره ميت


class Heartbeat:
    """
    يدير نبضات الحياة لـ Worker معيّن.
    
    - يبعت نبضة كل ثانية إلى Redis Hash
    - ينظّف الـ workers الميتين تلقائيًا
    """

    def __init__(self, redis: aioredis.Redis, worker_id: str):
        self.redis = redis
        self.worker_id = worker_id
        self._task: Optional[asyncio.Task] = None
        self._running = False

    async def _beat_loop(self):
        """يبعت نبضة كل ثانية"""
        key = f"worker:heartbeat:{self.worker_id}"
        while self._running:
            try:
                payload = {
                    "worker_id": self.worker_id,
                    "timestamp": time.time(),
                }
                await self.redis.setex(
                    key,
                    HEARTBEAT_TTL,
                    json.dumps(payload),
                )
            except Exception as e:
                print(f"[{self.worker_id}] Heartbeat error: {e}")
            await asyncio.sleep(HEARTBEAT_INTERVAL)

    async def start(self):
        """يبدأ إرسال النبضات"""
        self._running = True
        self._task = asyncio.create_task(self._beat_loop())

    async def stop(self):
        """يوقف النبضات وينظّف المفتاح"""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        await self.redis.delete(f"worker:heartbeat:{self.worker_id}")

    @staticmethod
    async def get_alive_workers(redis: aioredis.Redis) -> list:
        """يرجع قائمة الـ Workers الأحياء (اللي عندهم نبضة)"""
        keys = await redis.keys("worker:heartbeat:*")
        alive = []
        for key in keys:
            raw = await redis.get(key)
            if raw:
                try:
                    data = json.loads(raw)
                    alive.append(data["worker_id"])
                except Exception:
                    pass
        return alive

    @staticmethod
    async def is_alive(redis: aioredis.Redis, worker_id: str) -> bool:
        """يتحقق إذا Worker معيّن حي"""
        return await redis.exists(f"worker:heartbeat:{worker_id}") > 0