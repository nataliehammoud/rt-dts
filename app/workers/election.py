"""
Leader Election
===============
اختيار قائد واحد بين الـ Workers باستخدام Redis SETNX + TTL
"""
import asyncio
import time
from typing import Optional
import redis.asyncio as aioredis


LEADER_KEY = "cluster:leader"
LEADER_TTL = 10              # ثواني — القائد لازم يجدّد قبل انتهاء المدة
RENEW_INTERVAL = 5           # ثواني — يجدّد كل 5 ثواني


class LeaderElection:
    """
    Leader Election بسيط:
    - أول Worker ياخد المفتاح بـ SET NX يصير Leader
    - القائد يجدّد الـ TTL كل 5 ثواني
    - إذا مات القائد، الـ TTL ينتهي و Worker تاني ياخده
    """

    def __init__(self, redis: aioredis.Redis, worker_id: str):
        self.redis = redis
        self.worker_id = worker_id
        self.is_leader = False
        self._task: Optional[asyncio.Task] = None
        self._running = False

    async def _try_acquire(self) -> bool:
        """يحاول يصير Leader"""
        # SET NX = فقط إذا المفتاح غير موجود
        acquired = await self.redis.set(
            LEADER_KEY,
            self.worker_id,
            nx=True,
            ex=LEADER_TTL,
        )
        if acquired:
            return True

        # إذا المفتاح موجود، شوف إذا هو لنا (نحن القائد الحالي)
        current = await self.redis.get(LEADER_KEY)
        return current == self.worker_id

    async def _renew_loop(self):
        """يحاول يصير/يفضل Leader"""
        while self._running:
            try:
                was_leader = self.is_leader
                self.is_leader = await self._try_acquire()

                # إذا صار Leader للتو
                if self.is_leader and not was_leader:
                    print(f"👑 [{self.worker_id}] BECAME LEADER")
                    await self.redis.publish(
                        "cluster:events",
                        f"leader_elected:{self.worker_id}",
                    )
                # إذا خسر الـ Leadership
                elif not self.is_leader and was_leader:
                    print(f"❌ [{self.worker_id}] LOST LEADERSHIP")

                # إذا القائد، جدّد الـ TTL
                if self.is_leader:
                    await self.redis.expire(LEADER_KEY, LEADER_TTL)

            except Exception as e:
                print(f"[{self.worker_id}] Election error: {e}")
            await asyncio.sleep(RENEW_INTERVAL)

    async def start(self):
        """يبدأ محاولات الانتخاب"""
        self._running = True
        self._task = asyncio.create_task(self._renew_loop())

    async def stop(self):
        """يوقف ويحرّر الـ Leadership إذا كان قائدًا"""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        # إذا نحن القائد، احذف المفتاح
        current = await self.redis.get(LEADER_KEY)
        if current == self.worker_id:
            await self.redis.delete(LEADER_KEY)
            await self.redis.publish(
                "cluster:events",
                f"leader_released:{self.worker_id}",
            )

    @staticmethod
    async def get_current_leader(redis: aioredis.Redis) -> Optional[str]:
        """يرجع اسم القائد الحالي"""
        return await redis.get(LEADER_KEY)