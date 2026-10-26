"""
Worker Runner
=============
نقطة تشغيل Worker واحد.
استخدام: python -m app.workers.runner
"""
import asyncio
import signal
import sys

from app.core.logging import setup_logging, get_logger
from app.core.redis_client import redis_client, close_redis
from app.workers.worker import Worker

logger = get_logger(__name__)


async def main():
    setup_logging("INFO")

    worker_id = sys.argv[1] if len(sys.argv) > 1 else None
    worker = Worker(redis_client, worker_id=worker_id)

    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()

    def _signal_handler():
        logger.info(f"received_shutdown_signal worker_id={worker.worker_id}")
        stop_event.set()

    try:
        loop.add_signal_handler(signal.SIGINT, _signal_handler)
        loop.add_signal_handler(signal.SIGTERM, _signal_handler)
    except NotImplementedError:
        pass

    worker_task = asyncio.create_task(worker.start())

    await stop_event.wait()

    worker_task.cancel()
    try:
        await worker_task
    except asyncio.CancelledError:
        pass

    await worker.stop()
    await close_redis()
    logger.info(f"shutdown_complete worker_id={worker.worker_id}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("interrupted_by_user")