"""
Leader Election
===============
قيادة واحدة فقط، مع تجديد TTL ذري (Lua script).
"""
import asyncio
import redis.asyncio as aioredis

from app.core.logging import get_logger

logger = get_logger(__name__)

LEADER_KEY = "workers:leader"
LEADER_TTL = 10
RENEW_INTERVAL = 5

RENEW_SCRIPT = """
if redis.call("GET", KEYS[1]) == ARGV[1] then
    return redis.call("EXPIRE", KEYS[1], ARGV[2])
else
    return 0
end
"""

RELEASE_SCRIPT = """
if redis.call("GET", KEYS[1]) == ARGV[1] then
    return redis.call("DEL", KEYS[1])
else
    return 0
end
"""


class LeaderElection:
    def __init__(self, redis: aioredis.Redis, worker_id: str):
        self.redis = redis
        self.worker_id = worker_id
        self.is_leader = False
        self._running = False
        self._task = None

    async def _try_acquire(self) -> bool:
        acquired = await self.redis.set(
            LEADER_KEY, self.worker_id, nx=True, ex=LEADER_TTL
        )
        if acquired:
            self.is_leader = True
            logger.info(f"leader_acquired worker_id={self.worker_id}")
        return bool(acquired)

    async def _renew(self) -> bool:
        result = await self.redis.eval(
            RENEW_SCRIPT, 1, LEADER_KEY, self.worker_id, LEADER_TTL
        )
        return int(result) == 1

    async def _renew_loop(self):
        while self._running:
            try:
                if self.is_leader:
                    if not await self._renew():
                        logger.warning(f"leader_lost worker_id={self.worker_id}")
                        self.is_leader = False
                else:
                    await self._try_acquire()
            except Exception as e:
                logger.error(f"election_error worker_id={self.worker_id} error={e}")
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
            await self.redis.eval(RELEASE_SCRIPT, 1, LEADER_KEY, self.worker_id)
            logger.info(f"leader_released worker_id={self.worker_id}")
        self.is_leader = False