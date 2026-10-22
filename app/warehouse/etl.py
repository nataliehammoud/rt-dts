"""
ETL Job
=======
Extract-Transform-Load
- يسحب من جداول التشغيل (tasks)
- يحوّل للشكل التحليلي (Star Schema)
- يحمّل في جداول Warehouse

يعمل كل دقيقة (configurable).
يتعامل مع التكرار عبر Redis (last_task_id).
"""
import asyncio
from datetime import datetime
from typing import Optional

import redis.asyncio as aioredis
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.db.models import Task, TaskStatus
from app.warehouse.models import (
    DimTask,
    DimWorker,
    DimStatus,
    DimTime,
    FactTaskExecution,
)


LAST_TASK_ID_KEY = "warehouse:last_task_id"


# Cache للـ dimension IDs (لتجنب queries متكررة)
_dim_cache: dict = {
    "tasks": {},
    "workers": {},
    "statuses": {},
    "times": {},
}


def _get_or_create_dim_task(db: Session, task: Task) -> int:
    if task.id in _dim_cache["tasks"]:
        return _dim_cache["tasks"][task.id]

    dim = db.query(DimTask).filter(DimTask.task_id == task.id).first()
    if not dim:
        dim = DimTask(
            task_id=task.id,
            name=task.name,
            duration=task.duration,
            period=task.period,
            deadline=task.deadline,
        )
        db.add(dim)
        db.flush()

    _dim_cache["tasks"][task.id] = dim.id
    return dim.id


def _get_or_create_dim_worker(db: Session, worker_id: str) -> int:
    if worker_id in _dim_cache["workers"]:
        return _dim_cache["workers"][worker_id]

    now = datetime.utcnow()
    dim = db.query(DimWorker).filter(DimWorker.worker_id == worker_id).first()

    if not dim:
        dim = DimWorker(worker_id=worker_id, first_seen=now, last_seen=now)
        db.add(dim)
        db.flush()
    else:
        dim.last_seen = now

    _dim_cache["workers"][worker_id] = dim.id
    return dim.id


def _get_or_create_dim_status(db: Session, status_name: str) -> int:
    if status_name in _dim_cache["statuses"]:
        return _dim_cache["statuses"][status_name]

    dim = db.query(DimStatus).filter(DimStatus.name == status_name).first()
    if not dim:
        dim = DimStatus(name=status_name, description=f"Status: {status_name}")
        db.add(dim)
        db.flush()

    _dim_cache["statuses"][status_name] = dim.id
    return dim.id


def _get_or_create_dim_time(db: Session, dt: datetime) -> int:
    dt = dt.replace(second=0, microsecond=0)

    if dt in _dim_cache["times"]:
        return _dim_cache["times"][dt]

    dim = db.query(DimTime).filter(DimTime.full_date == dt).first()
    if not dim:
        dim = DimTime(
            full_date=dt,
            year=dt.year,
            month=dt.month,
            day=dt.day,
            hour=dt.hour,
            minute=dt.minute,
            day_of_week=dt.weekday(),
            is_weekend=1 if dt.weekday() >= 5 else 0,
        )
        db.add(dim)
        db.flush()

    _dim_cache["times"][dt] = dim.id
    return dim.id


def _compute_durations(task: Task) -> tuple:
    """
    يرجع (execution_time, total_time) بالثواني.
    - execution_time: مدة المهمة الفعلية (duration)
    - total_time: الوقت الحقيقي من started_at إلى finished_at (لو متوفر)
    """
    execution_time = float(task.duration or 0.0)

    if task.started_at and task.finished_at:
        delta = (task.finished_at - task.started_at).total_seconds()
        total_time = max(delta, execution_time)
    else:
        total_time = execution_time

    return execution_time, total_time


async def run_etl_once(redis: aioredis.Redis) -> dict:
    """يشغّل ETL مرة وحدة. يعيد إحصائيات."""
    db = SessionLocal()
    stats = {"scanned": 0, "inserted": 0, "skipped": 0}

    try:
        last_id_raw = await redis.get(LAST_TASK_ID_KEY)
        last_id = int(last_id_raw) if last_id_raw else 0

        # جلب فقط المهام المكتملة/الفاشلة الجديدة
        tasks = (
            db.query(Task)
            .filter(Task.id > last_id)
            .filter(Task.status.in_(["completed", "failed"]))
            .order_by(Task.id)
            .all()
        )

        stats["scanned"] = len(tasks)
        max_id = last_id

        for task in tasks:
            dim_task_id = _get_or_create_dim_task(db, task)

            # تحقق إذا موجود في fact
            existing = (
                db.query(FactTaskExecution)
                .filter(FactTaskExecution.task_id == dim_task_id)
                .first()
            )

            if existing:
                stats["skipped"] += 1
                max_id = max(max_id, task.id)
                continue

            # ✅ worker_id الحقيقي من DB (مو placeholder)
            real_worker = task.worker_id or "unknown-worker"
            dim_worker_id = _get_or_create_dim_worker(db, real_worker)

            # ✅ status كـ string نظيف (مو enum)
            status_value = (
                task.status.value
                if hasattr(task.status, "value")
                else str(task.status)
            )
            dim_status_id = _get_or_create_dim_status(db, status_value)

            # ✅ وقت التنفيذ الفعلي
            time_ref = task.finished_at or task.created_at or datetime.utcnow()
            dim_time_id = _get_or_create_dim_time(db, time_ref)

            # ✅ حساب الأوقات الحقيقية
            execution_time, total_time = _compute_durations(task)

            fact = FactTaskExecution(
                task_id=dim_task_id,
                worker_id=dim_worker_id,
                status_id=dim_status_id,
                time_id=dim_time_id,
                execution_time=execution_time,
                total_time=total_time,
                attempts=1,
                deadline_met=1,
            )
            db.add(fact)
            stats["inserted"] += 1
            max_id = max(max_id, task.id)

        db.commit()

        if max_id > last_id:
            await redis.set(LAST_TASK_ID_KEY, str(max_id))

    except Exception as e:
        db.rollback()
        print(f"❌ ETL error: {e}", flush=True)
        raise
    finally:
        db.close()

    return stats


async def etl_worker(redis: aioredis.Redis, interval_seconds: int = 60):
    """ETL Job يعمل كل `interval_seconds` ثانية."""
    print(f"🔄 ETL worker started (every {interval_seconds}s)", flush=True)

    while True:
        try:
            await asyncio.sleep(interval_seconds)
            stats = await run_etl_once(redis)
            if stats["inserted"] > 0 or stats["scanned"] > 0:
                print(
                    f"✅ ETL: scanned={stats['scanned']}, "
                    f"inserted={stats['inserted']}, skipped={stats['skipped']}",
                    flush=True,
                )
        except asyncio.CancelledError:
            print("🔄 ETL worker stopped", flush=True)
            break
        except Exception as e:
            print(f"❌ ETL worker error: {e}", flush=True)