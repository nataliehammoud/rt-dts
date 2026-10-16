"""
Dead Letter Queue
=================
مكان للمهام اللي فشلت نهائيًا (بعد كل محاولات Retry)
"""
import json
import time
from typing import Optional, List
import redis.asyncio as aioredis


DLQ_KEY = "tasks:dlq"           # Redis List
DLQ_MAX_SIZE = 1000             # حد أقصى (نتجنب امتلاء Redis)


class DeadLetterQueue:
    """
    DLQ بسيط على Redis List.
    
    - push: يضيف مهمة فاشلة مع سبب الفشل وعدد المحاولات
    - peek: يشوف آخر N مهام بدون حذف
    - pop: يسحب مهمة (للإعادة اليدوية)
    - size: عدد المهام في DLQ
    """

    def __init__(self, redis: aioredis.Redis):
        self.redis = redis

    async def push(
        self,
        task: dict,
        reason: str,
        attempts: int,
    ):
        """يضيف مهمة فاشلة للـ DLQ"""
        entry = {
            "task": task,
            "reason": reason,
            "attempts": attempts,
            "failed_at": time.time(),
        }
        await self.redis.lpush(DLQ_KEY, json.dumps(entry))

        # Trim: نحتفظ بآخر DLQ_MAX_SIZE فقط
        await self.redis.ltrim(DLQ_KEY, 0, DLQ_MAX_SIZE - 1)

    async def peek(self, count: int = 10) -> List[dict]:
        """يشوف آخر N مهمة بدون حذف"""
        raw_items = await self.redis.lrange(DLQ_KEY, 0, count - 1)
        result = []
        for raw in raw_items:
            try:
                result.append(json.loads(raw))
            except json.JSONDecodeError:
                continue
        return result

    async def pop(self) -> Optional[dict]:
        """يسحب مهمة من الـ DLQ (للإعادة)"""
        raw = await self.redis.rpop(DLQ_KEY)
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return None

    async def size(self) -> int:
        """عدد المهام الفاشلة"""
        return await self.redis.llen(DLQ_KEY)

    async def clear(self):
        """يحذف كل المهام"""
        await self.redis.delete(DLQ_KEY)