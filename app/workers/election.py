"""
Leader Election
===============
قيادة واحدة فقط، مع تجديد TTL آمن.
يتعامل مع decode_responses سواء True أو False.
"""
import asyncio
import redis.asyncio as aioredis


LEADER_KEY = "workers:leader"
LEADER_TTL = 10        # ثواني
RENEW_INTERVAL = 5     # ثواني


def _as_str(value) -> str | None:
    """يرجع str سواء كان bytes أو str (يتعامل مع decode_responses)."""
    if value is None:
        return None
    if isinstance(value, bytes):
        return value.decode()
    return str(value)


class LeaderElection:
    def __init__(self, redis: aioredis.Redis, worker_id: str):
        self.redis = redis
        self.worker_id = worker_id
        self.is_leader = False
        self._running = False
        self._task: asyncio.Task | None = None

    async def _try_acquire(self) -> bool:
        acquired = await self.redis.set(
            LEADER_KEY, self.worker_id, nx=True, ex=LEADER_TTL
        )
        if acquired:
            self.is_leader = True
            print(f"[{self.worker_id}] ✅ Acquired leadership", flush=True)
        return bool(acquired)

    async def _renew(self) -> bool:
        """
        FIX: جدّدي TTL فقط إذا لسا إنتي الـ leader.
        يشتغل مع bytes و str (decode_responses=True أو False).
        """
        try:
            current = await self.redis.get(LEADER_KEY)
            current_str = _as_str(current)
            if current_str == self.worker_id:
                await self.redis.expire(LEADER_KEY, LEADER_TTL)
                return True
            return False
        except Exception as e:
            print(f"[{self.worker_id}] ⚠️ _renew error: {e}", flush=True)
            return False

    async def _renew_loop(self):
        while self._running:
            try:
                if self.is_leader:
                    if not await self._renew():
                        print(f"[{self.worker_id}] ⚠️ Lost leadership", flush=True)
                        self.is_leader = False
                        # حاولي فورًا تعيدي الاستحواذ
                        await self._try_acquire()
                else:
                    await self._try_acquire()
            except Exception as e:
                print(f"[{self.worker_id}] Election error: {e}", flush=True)
            await asyncio.sleep(RENEW_INTERVAL)

    async def start(self):
        self._running = True
        self._task = asyncio.create_task(self._renew_loop())

    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

        if self.is_leader:
            try:
                current = await self.redis.get(LEADER_KEY)
                if _as_str(current) == self.worker_id:
                    await self.redis.delete(LEADER_KEY)
                    print(f"[{self.worker_id}] 👋 Released leadership cleanly", flush=True)
            except Exception as e:
                print(f"[{self.worker_id}] Release error: {e}", flush=True)
        self.is_leader = False