"""
Schedulability Tests
====================
اختبارات قابلية الجدولة
"""
import math
from typing import List
from app.scheduler.models import RTTask


def rm_schedulability_bound(tasks: List[RTTask]) -> float:
    """
    حد Liu & Layland لـ RM:
    n * (2^(1/n) - 1)
    """
    n = len(tasks)
    if n == 0:
        return 1.0
    return n * (2 ** (1 / n) - 1)


def rm_is_schedulable(tasks: List[RTTask]) -> bool:
    """
    اختبار كافٍ (Sufficient) لـ RM.
    إذا U <= bound → مضمون الجدولة.
    """
    u = sum(t.utilization for t in tasks)
    return u <= rm_schedulability_bound(tasks)


def edf_is_schedulable(tasks: List[RTTask]) -> bool:
    """
    اختبار ضروري وكافٍ لـ EDF.
    U <= 1 → مجدول.
    """
    u = sum(t.utilization for t in tasks)
    return u <= 1.0


def response_time_analysis(task: RTTask, higher_priority: List[RTTask]) -> float:
    """
    حساب Worst-Case Response Time (RTA) لمهمة.
    
    R = C + sum(ceil(R/Tj) * Cj)
    
    نكرر لين R يستقر.
    """
    R = task.wcet
    for _ in range(100):
        interference = sum(
            math.ceil(R / hp.period) * hp.wcet
            for hp in higher_priority
        )
        new_R = task.wcet + interference
        if abs(new_R - R) < 1e-9:
            return R
        R = new_R
    return R


def rm_is_schedulable_exact(tasks: List[RTTask]) -> bool:
    """
    اختبار دقيق (Necessary & Sufficient) لـ RM باستخدام RTA.
    
    لكل مهمة، نحسب Worst-Case Response Time ونقارنه بـ deadline.
    إذا كل المهام R <= D → مجدول.
    """
    sorted_tasks = sorted(tasks, key=lambda t: t.period)
    for i, task in enumerate(sorted_tasks):
        higher_priority = sorted_tasks[:i]
        r = response_time_analysis(task, higher_priority)
        if r > task.deadline:
            return False
    return True


def task_set_utilization(tasks: List[RTTask]) -> float:
    """حساب U الكلي"""
    return sum(t.utilization for t in tasks)