"""
Stuck Task Cleanup
==================
يرجع المهام العالقة (running > threshold) لـ failed.
"""
import asyncio
from datetime import datetime, timedelta

from app.core.logging import get_logger
from app.db.session import SessionLocal
from app.db.models import Task, TaskStatus

logger = get_logger(__name__)

STUCK_THRESHOLD_MINUTES = 5
CLEANUP_INTERVAL_SECONDS = 60


def cleanup_once(threshold_minutes: int = STUCK_THRESHOLD_MINUTES) -> int:
    db = SessionLocal()
    try:
        cutoff = datetime.utcnow() - timedelta(minutes=threshold_minutes)
        stuck = (
            db.query(Task)
            .filter(Task.status == TaskStatus.running.value)
            .filter(Task.started_at.isnot(None))
            .filter(Task.started_at < cutoff)
            .all()
        )
        for task in stuck:
            task.status = TaskStatus.failed.value
            task.finished_at = datetime.utcnow()

        db.commit()
        return len(stuck)
    except Exception as e:
        db.rollback()
        logger.error(f"cleanup_error error={e}")
        return 0
    finally:
        db.close()


async def cleanup_worker(interval_seconds: int = CLEANUP_INTERVAL_SECONDS):
    logger.info(f"cleanup_worker_started interval={interval_seconds}")
    while True:
        try:
            await asyncio.sleep(interval_seconds)
            count = cleanup_once()
            if count > 0:
                logger.info(f"cleaned_stuck_tasks count={count}")
        except asyncio.CancelledError:
            logger.info("cleanup_worker_stopped")
            break
        except Exception as e:
            logger.error(f"cleanup_worker_error error={e}")