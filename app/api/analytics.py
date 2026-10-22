"""
Analytics API (OLAP)
====================
استعلامات تحليلية على الـ Data Warehouse
"""
from fastapi import APIRouter, Depends
from sqlalchemy import func, desc, case
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List

from app.db.session import get_db
from app.warehouse.models import (
    FactTaskExecution,
    DimTask,
    DimWorker,
    DimStatus,
    DimTime,
)


router = APIRouter(prefix="/analytics", tags=["analytics"])


# ============================================================
# Schemas
# ============================================================

class WorkerStats(BaseModel):
    worker_id: str
    total_tasks: int
    completed: int
    failed: int
    avg_execution_time: float
    success_rate: float


class TaskStats(BaseModel):
    task_name: str
    total_executions: int
    avg_execution_time: float
    deadline_met_count: int


class TimelinePoint(BaseModel):
    date: str
    hour: int
    completed: int
    failed: int


class SummaryStats(BaseModel):
    total_executions: int
    completed: int
    failed: int
    success_rate: float
    avg_execution_time: float
    active_workers: int
    deadline_met_rate: float


# ============================================================
# Endpoints
# ============================================================

@router.get("/workers", response_model=List[WorkerStats])
def get_worker_stats(db: Session = Depends(get_db)):
    """
    إحصائيات لكل Worker.
    """
    results = (
        db.query(
            DimWorker.worker_id,
            func.count(FactTaskExecution.id).label("total"),
            func.sum(
                case((DimStatus.name == "completed", 1), else_=0)
            ).label("completed"),
            func.sum(
                case((DimStatus.name == "failed", 1), else_=0)
            ).label("failed"),
            func.avg(FactTaskExecution.execution_time).label("avg_time"),
        )
        .join(FactTaskExecution, FactTaskExecution.worker_id == DimWorker.id)
        .join(DimStatus, DimStatus.id == FactTaskExecution.status_id)
        .group_by(DimWorker.worker_id)
        .all()
    )

    stats = []
    for r in results:
        total = int(r.total or 0)
        completed = int(r.completed or 0)
        stats.append(WorkerStats(
            worker_id=r.worker_id,
            total_tasks=total,
            completed=completed,
            failed=int(r.failed or 0),
            avg_execution_time=float(r.avg_time or 0),
            success_rate=round(completed / total * 100, 2) if total > 0 else 0,
        ))
    return stats


@router.get("/tasks", response_model=List[TaskStats])
def get_task_stats(db: Session = Depends(get_db)):
    results = (
        db.query(
            DimTask.name,
            func.count(FactTaskExecution.id).label("total"),
            func.avg(FactTaskExecution.execution_time).label("avg_time"),
            func.sum(FactTaskExecution.deadline_met).label("deadline_met"),
        )
        .join(FactTaskExecution, FactTaskExecution.task_id == DimTask.id)
        .group_by(DimTask.name)
        .order_by(desc(func.count(FactTaskExecution.id)))
        .limit(20)
        .all()
    )

    return [
        TaskStats(
            task_name=r.name,
            total_executions=int(r.total or 0),
            avg_execution_time=float(r.avg_time or 0),
            deadline_met_count=int(r.deadline_met or 0),
        )
        for r in results
    ]


@router.get("/timeline", response_model=List[TimelinePoint])
def get_timeline(db: Session = Depends(get_db), limit: int = 100):
    results = (
        db.query(
            DimTime.full_date,
            DimTime.hour,
            DimStatus.name,
            func.count(FactTaskExecution.id).label("count"),
        )
        .join(FactTaskExecution, FactTaskExecution.time_id == DimTime.id)
        .join(DimStatus, DimStatus.id == FactTaskExecution.status_id)
        .group_by(DimTime.full_date, DimTime.hour, DimStatus.name)
        .order_by(desc(DimTime.full_date))
        .limit(limit)
        .all()
    )

    buckets = {}
    for r in results:
        key = (r.full_date.date().isoformat() if r.full_date else "?", r.hour or 0)
        if key not in buckets:
            buckets[key] = {"date": key[0], "hour": key[1], "completed": 0, "failed": 0}
        if r.name == "completed":
            buckets[key]["completed"] += r.count
        elif r.name == "failed":
            buckets[key]["failed"] += r.count

    return [
        TimelinePoint(**b)
        for b in sorted(buckets.values(), key=lambda x: (x["date"], x["hour"]))
    ]


@router.get("/summary", response_model=SummaryStats)
def get_summary(db: Session = Depends(get_db)):
    total = db.query(func.count(FactTaskExecution.id)).scalar() or 0

    completed = (
        db.query(func.count(FactTaskExecution.id))
        .join(DimStatus, DimStatus.id == FactTaskExecution.status_id)
        .filter(DimStatus.name == "completed")
        .scalar()
        or 0
    )

    failed = (
        db.query(func.count(FactTaskExecution.id))
        .join(DimStatus, DimStatus.id == FactTaskExecution.status_id)
        .filter(DimStatus.name == "failed")
        .scalar()
        or 0
    )

    avg_time = db.query(func.avg(FactTaskExecution.execution_time)).scalar() or 0
    active_workers = db.query(func.count(func.distinct(FactTaskExecution.worker_id))).scalar() or 0
    deadline_met = db.query(func.sum(FactTaskExecution.deadline_met)).scalar() or 0

    return SummaryStats(
        total_executions=int(total),
        completed=int(completed),
        failed=int(failed),
        success_rate=round(completed / total * 100, 2) if total > 0 else 0,
        avg_execution_time=float(avg_time),
        active_workers=int(active_workers),
        deadline_met_rate=round(deadline_met / total * 100, 2) if total > 0 else 0,
    )