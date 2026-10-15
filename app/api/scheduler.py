"""
Scheduler API
=============
Endpoints لعرض واختبار خوارزميات الجدولة
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional

from app.scheduler.models import RTTask
from app.scheduler.rm import simulate_rm, assign_rm_priorities, get_rm_priority_order
from app.scheduler.edf import simulate_edf
from app.scheduler.tests import (
    rm_is_schedulable,
    rm_is_schedulable_exact,
    edf_is_schedulable,
    rm_schedulability_bound,
    task_set_utilization,
)


router = APIRouter(prefix="/scheduler", tags=["scheduler"])


# ============================================================
# Pydantic Schemas
# ============================================================

class TaskIn(BaseModel):
    name: str
    wcet: float = Field(..., gt=0, description="Worst-Case Execution Time")
    period: float = Field(..., gt=0, description="Period")
    deadline: Optional[float] = Field(None, description="Relative Deadline (default = period)")


class TaskSetIn(BaseModel):
    tasks: List[TaskIn]
    until: float = Field(20.0, gt=0, description="وقت المحاكاة")


class AnalysisOut(BaseModel):
    utilization: float
    ll_bound: float
    rm_ll_schedulable: bool
    rm_exact_schedulable: bool
    edf_schedulable: bool
    rm_priority_order: List[str]


class SimEventOut(BaseModel):
    task_name: str
    start: float
    end: float


class SimulationOut(BaseModel):
    algorithm: str
    context_switches: int
    deadline_misses: int
    total_time: float
    events_count: int
    events: List[SimEventOut]


# ============================================================
# Helpers
# ============================================================

def _to_rt_tasks(payload_tasks: List[TaskIn]) -> List[RTTask]:
    return [
        RTTask(name=t.name, wcet=t.wcet, period=t.period, deadline=t.deadline)
        for t in payload_tasks
    ]


# ============================================================
# Endpoints
# ============================================================

@router.post("/analyze", response_model=AnalysisOut)
def analyze(payload: TaskSetIn):
    """
    تحليل مجموعة مهام:
    - Utilization
    - LL Bound
    - RM Schedulability (LL + Exact)
    - EDF Schedulability
    - ترتيب الأولويات
    """
    if not payload.tasks:
        raise HTTPException(status_code=400, detail="Task set is empty")

    tasks = _to_rt_tasks(payload.tasks)

    return AnalysisOut(
        utilization=task_set_utilization(tasks),
        ll_bound=rm_schedulability_bound(tasks),
        rm_ll_schedulable=rm_is_schedulable(tasks),
        rm_exact_schedulable=rm_is_schedulable_exact(tasks),
        edf_schedulable=edf_is_schedulable(tasks),
        rm_priority_order=get_rm_priority_order(tasks),
    )


@router.post("/simulate/rm", response_model=SimulationOut)
def simulate_rate_monotonic(payload: TaskSetIn):
    """محاكاة جدولة RM"""
    if not payload.tasks:
        raise HTTPException(status_code=400, detail="Task set is empty")

    tasks = _to_rt_tasks(payload.tasks)
    result = simulate_rm(tasks, until=payload.until)

    return SimulationOut(
        algorithm="RM",
        context_switches=result.context_switches,
        deadline_misses=result.deadline_misses,
        total_time=result.total_time,
        events_count=len(result.events),
        events=[
            SimEventOut(task_name=e.task_name, start=e.start, end=e.end)
            for e in result.events
        ],
    )


@router.post("/simulate/edf", response_model=SimulationOut)
def simulate_edf_endpoint(payload: TaskSetIn):
    """محاكاة جدولة EDF"""
    if not payload.tasks:
        raise HTTPException(status_code=400, detail="Task set is empty")

    tasks = _to_rt_tasks(payload.tasks)
    result = simulate_edf(tasks, until=payload.until)

    return SimulationOut(
        algorithm="EDF",
        context_switches=result.context_switches,
        deadline_misses=result.deadline_misses,
        total_time=result.total_time,
        events_count=len(result.events),
        events=[
            SimEventOut(task_name=e.task_name, start=e.start, end=e.end)
            for e in result.events
        ],
    )