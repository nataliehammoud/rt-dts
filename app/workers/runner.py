"""
Worker Runner
=============
نقطة تشغيل Worker واحد.
استخدام: python -m app.workers.runner
"""
import asyncio
import signal
import sys

from app.core.redis_client import redis_client, close_redis
from app.workers.worker import Worker


async def main():
    worker_id = sys.argv[1] if len(sys.argv) > 1 else None
    worker = Worker(redis_client, worker_id=worker_id)

    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()

    def _signal_handler():
        print(f"\n[{worker.worker_id}] Received shutdown signal")
        stop_event.set()

    # التعامل مع Ctrl+C
    try:
        loop.add_signal_handler(signal.SIGINT, _signal_handler)
        loop.add_signal_handler(signal.SIGTERM, _signal_handler)
    except NotImplementedError:
        # Windows ما بيدعم add_signal_handler
        pass

    # شغّل الـ Worker في task منفصل
    worker_task = asyncio.create_task(worker.start())

    # انتظر إشارة الإيقاف
    await stop_event.wait()

    # إيقاف نظيف
    worker_task.cancel()
    try:
        await worker_task
    except asyncio.CancelledError:
        pass

    await worker.stop()
    await close_redis()
    print(f"[{worker.worker_id}] Shutdown complete.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nInterrupted by user.")