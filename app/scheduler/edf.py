"""
Earliest Deadline First Scheduler
==================================
خوارزمية EDF: أولوية أعلى للمهام ذات الموعد النهائي الأقرب.
Dynamic Priority Preemptive Scheduling — Optimal
"""
from typing import List
from app.scheduler.models import RTTask, ScheduleEvent, ScheduleResult


def simulate_edf(tasks: List[RTTask], until: float = 20.0, step: float = 0.1) -> ScheduleResult:
    """
    محاكاة جدولة EDF.
    
    الفرق عن RM:
    - الأولوية ديناميكية (تُحسب وقت التشغيل)
    - المعيار: absolute deadline (وليس period)
    """
    if not tasks:
        return ScheduleResult()

    # حالة كل مهمة
    releases = {t.name: 0.0 for t in tasks}
    remaining = {t.name: 0.0 for t in tasks}
    abs_deadlines = {t.name: float('inf') for t in tasks}

    result = ScheduleResult(total_time=until)
    current_time = 0.0
    last_task_name = None
    current_event = None

    while current_time < until - 1e-9:
        # 1) إطلاق المهام الجديدة
        for t in tasks:
            if abs(current_time - releases[t.name]) < 1e-9:
                remaining[t.name] = t.wcet
                abs_deadlines[t.name] = current_time + t.deadline
                releases[t.name] += t.period

        # 2) اختيار أقرب absolute deadline
        ready = [t for t in tasks if remaining[t.name] > 1e-9]
        ready.sort(key=lambda t: abs_deadlines[t.name])
        chosen = ready[0] if ready else None

        chosen_name = chosen.name if chosen else None

        # 3) Context switch tracking
        if chosen_name != last_task_name and chosen_name is not None:
            result.context_switches += 1
            if current_event:
                current_event.end = current_time
                result.events.append(current_event)
            current_event = ScheduleEvent(
                task_name=chosen_name,
                start=current_time,
                end=current_time,
            )
        last_task_name = chosen_name

        # 4) تنفيذ خطوة
        if chosen:
            remaining[chosen.name] = max(0.0, remaining[chosen.name] - step)

            if remaining[chosen.name] <= 1e-9:
                if current_time + step > abs_deadlines[chosen.name] + 1e-9:
                    result.deadline_misses += 1

        current_time += step

    if current_event:
        current_event.end = current_time
        result.events.append(current_event)

    return result


def get_edf_priority_order(tasks: List[RTTask], current_time: float = 0.0) -> List[str]:
    """
    يرجع ترتيب EDF الحالي (لحظة زمنية معينة).
    الأولوية حسب absolute deadline.
    """
    order = []
    for t in tasks:
        # نحسب الـ deadline الحالي
        cycles = int(current_time // t.period)
        next_release = cycles * t.period
        if next_release < current_time:
            next_release += t.period
        abs_dl = next_release + t.deadline
        order.append((t.name, abs_dl))
    order.sort(key=lambda x: x[1])
    return [name for name, _ in order]