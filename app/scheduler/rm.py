"""
Rate Monotonic Scheduler
========================
خوارزمية RM: أولوية أعلى للمهام ذات الفترة الأقصر.
Static Priority Preemptive Scheduling
"""
from typing import List
from app.scheduler.models import RTTask, ScheduleEvent, ScheduleResult


def assign_rm_priorities(tasks: List[RTTask]) -> List[RTTask]:
    """
    ترتيب المهام حسب RM:
    - Period أقصر → أولوية أعلى (priority = 1)
    - Period أطول → أولوية أقل (priority = n)
    """
    sorted_tasks = sorted(tasks, key=lambda t: t.period)
    for i, task in enumerate(sorted_tasks):
        task.priority = i + 1  # 1 = الأعلى
    return sorted_tasks


def simulate_rm(tasks: List[RTTask], until: float = 20.0, step: float = 0.1) -> ScheduleResult:
    """
    محاكاة جدولة RM.
    
    :param tasks: قائمة المهام
    :param until: وقت المحاكاة (افتراضي: 20 وحدة زمن)
    :param step: دقة المحاكاة (0.1 وحدة زمن)
    :return: ScheduleResult
    """
    if not tasks:
        return ScheduleResult()

    # ترتيب المهام حسب RM
    tasks = assign_rm_priorities(tasks)

    # حالة كل مهمة
    releases = {t.name: 0.0 for t in tasks}          # وقت الإطلاق القادم
    remaining = {t.name: 0.0 for t in tasks}          # المتبقي من التنفيذ
    abs_deadlines = {t.name: 0.0 for t in tasks}      # الموعد النهائي المطلق

    result = ScheduleResult(total_time=until)
    current_time = 0.0
    last_task_name = None
    current_event = None

    while current_time < until - 1e-9:
        # 1) إطلاق المهام الجديدة (periodic)
        for t in tasks:
            if abs(current_time - releases[t.name]) < 1e-9:
                remaining[t.name] = t.wcet
                abs_deadlines[t.name] = current_time + t.deadline
                releases[t.name] += t.period

        # 2) اختيار أعلى أولوية (priority أصغر رقم = أعلى)
        ready = [t for t in tasks if remaining[t.name] > 1e-9]
        ready.sort(key=lambda t: t.priority)
        chosen = ready[0] if ready else None

        chosen_name = chosen.name if chosen else None

        # 3) Context switch tracking
        if chosen_name != last_task_name and chosen_name is not None:
            result.context_switches += 1
            # إغلاق الحدث السابق
            if current_event:
                current_event.end = current_time
                result.events.append(current_event)
            # بدء حدث جديد
            current_event = ScheduleEvent(
                task_name=chosen_name,
                start=current_time,
                end=current_time,
            )
        last_task_name = chosen_name

        # 4) تنفيذ خطوة
        if chosen:
            remaining[chosen.name] = max(0.0, remaining[chosen.name] - step)

            # 5) فحص deadline miss عند الإكمال
            if remaining[chosen.name] <= 1e-9:
                if current_time + step > abs_deadlines[chosen.name] + 1e-9:
                    result.deadline_misses += 1

        current_time += step

    # إغلاق آخر حدث
    if current_event:
        current_event.end = current_time
        result.events.append(current_event)

    return result


def get_rm_priority_order(tasks: List[RTTask]) -> List[str]:
    """يرجع أسماء المهام مرتبة حسب أولوية RM"""
    sorted_tasks = sorted(tasks, key=lambda t: t.period)
    return [t.name for t in sorted_tasks]