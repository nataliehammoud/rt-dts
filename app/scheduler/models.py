"""
Real-Time Task Models
=====================
نماذج المهام في أنظمة الزمن الحقيقي
"""
from dataclasses import dataclass, field
from typing import Optional, List


@dataclass
class RTTask:
    """
    مهمة في نظام الزمن الحقيقي (Real-Time Task).
    
    الخصائص:
    - name: اسم المهمة
    - wcet: Worst-Case Execution Time (C) - أسوأ وقت تنفيذ
    - period: الفترة (T) - الوقت بين كل إطلاقين
    - deadline: الموعد النهائي النسبي (D) - لو None، D = T
    - priority: الأولوية (تُحسب حسب الخوارزمية)
    """
    name: str
    wcet: float
    period: float
    deadline: Optional[float] = None
    priority: int = 0

    def __post_init__(self):
        if self.deadline is None or self.deadline == 0:
            self.deadline = self.period

    @property
    def utilization(self) -> float:
        """نسبة استخدام المعالج = C/T"""
        return self.wcet / self.period


@dataclass
class ScheduleEvent:
    """حدث في الجدول الزمني"""
    task_name: str
    start: float
    end: float
    preempted: bool = False


@dataclass
class ScheduleResult:
    """نتيجة المحاكاة"""
    events: List[ScheduleEvent] = field(default_factory=list)
    context_switches: int = 0
    deadline_misses: int = 0
    total_time: float = 0.0

    def to_dict(self):
        return {
            "events_count": len(self.events),
            "context_switches": self.context_switches,
            "deadline_misses": self.deadline_misses,
            "total_time": self.total_time,
        }