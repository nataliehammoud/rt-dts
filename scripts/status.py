"""
Status Check
============
يعرض حالة النظام: Queue, DLQ, Workers, Leader.

الاستخدام:
    python scripts/status.py
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.redis_client import redis_client
from app.workers.worker import TASKS_QUEUE
from app.workers.heartbeat import Heartbeat
from app.distributed.dlq import DeadLetterQueue


async def main():
    queue_len = await redis_client.llen(TASKS_QUEUE)
    dlq_size = await DeadLetterQueue(redis_client).size()
    alive = await Heartbeat.get_alive_workers(redis_client)
    leader = await redis_client.get("cluster:leader")

    print("=" * 40)
    print(f"Queue:  {queue_len}")
    print(f"DLQ:    {dlq_size}")
    print(f"Alive:  {alive}")
    print(f"Leader: {leader}")
    print("=" * 40)

    await redis_client.aclose()


if __name__ == "__main__":
    asyncio.run(main())