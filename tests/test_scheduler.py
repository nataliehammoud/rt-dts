"""
Unit Tests for Scheduler
========================
اختبارات وحدة لخوارزميات الجدولة
"""
import pytest
from app.scheduler.models import RTTask
from app.scheduler.rm import simulate_rm, assign_rm_priorities, get_rm_priority_order
from app.scheduler.edf import simulate_edf
from app.scheduler.tests import (
    rm_is_schedulable,
    rm_is_schedulable_exact,
    edf_is_schedulable,
    rm_schedulability_bound,
    response_time_analysis,
    task_set_utilization,
)


# ============================================================
# Test Fixtures
# ============================================================

@pytest.fixture
def classic_task_set():
    """مجموعة مهام كلاسيكية (Liu & Layland)"""
    return [
        RTTask(name="T1", wcet=1, period=4, deadline=4),
        RTTask(name="T2", wcet=2, period=5, deadline=5),
        RTTask(name="T3", wcet=2, period=10, deadline=10),
    ]


@pytest.fixture
def overloaded_task_set():
    """مجموعة مهام غير قابلة للجدولة"""
    return [
        RTTask(name="A", wcet=3, period=4, deadline=4),
        RTTask(name="B", wcet=3, period=4, deadline=4),
    ]


# ============================================================
# RM Priority Tests
# ============================================================

def test_rm_priority_assignment(classic_task_set):
    """RM: المهمة ذات الفترة الأقصر تأخذ أولوية أعلى"""
    sorted_tasks = assign_rm_priorities(classic_task_set)
    assert sorted_tasks[0].name == "T1"  # period=4 → priority=1
    assert sorted_tasks[1].name == "T2"  # period=5 → priority=2
    assert sorted_tasks[2].name == "T3"  # period=10 → priority=3


def test_rm_priority_order(classic_task_set):
    order = get_rm_priority_order(classic_task_set)
    assert order == ["T1", "T2", "T3"]


# ============================================================
# Schedulability Tests
# ============================================================

def test_utilization(classic_task_set):
    """U = Σ(Ci/Ti)"""
    u = task_set_utilization(classic_task_set)
    expected = 1/4 + 2/5 + 2/10
    assert abs(u - expected) < 1e-9


def test_ll_bound_3_tasks(classic_task_set):
    """حد LL لـ 3 مهام: 3 * (2^(1/3) - 1) ≈ 0.779"""
    bound = rm_schedulability_bound(classic_task_set)
    expected = 3 * (2 ** (1/3) - 1)
    assert abs(bound - expected) < 1e-9


def test_rm_ll_bound_fails(classic_task_set):
    """
    U = 0.85 > LL bound (0.78) → LL test يفشل
    لكن هذا لا يعني أن المجموعة غير قابلة للجدولة!
    """
    from app.scheduler.tests import task_set_utilization
    u = task_set_utilization(classic_task_set)
    bound = rm_schedulability_bound(classic_task_set)
    assert u > bound  # LL bound test يفشل
    assert rm_is_schedulable(classic_task_set) is False


def test_rm_exact_schedulable(classic_task_set):
    """
    لكن بالاختبار الدقيق (RTA)، المجموعة قابلة للجدولة.
    هذا يثبت أن LL Bound شرط كافٍ لكن ليس ضروريًا.
    """
    from app.scheduler.tests import rm_is_schedulable_exact
    assert rm_is_schedulable_exact(classic_task_set) is True

def test_edf_schedulable(classic_task_set):
    """هذه المجموعة قابلة للجدولة بـ EDF"""
    assert edf_is_schedulable(classic_task_set) is True


def test_edf_not_schedulable(overloaded_task_set):
    """U = 1.5 > 1 → غير قابل للجدولة بـ EDF"""
    assert edf_is_schedulable(overloaded_task_set) is False


# ============================================================
# Response Time Analysis
# ============================================================

def test_rta_highest_priority(classic_task_set):
    """T1 هو الأعلى → R = C = 1"""
    t1 = classic_task_set[0]
    r = response_time_analysis(t1, [])
    assert abs(r - 1.0) < 1e-9


def test_rta_t2(classic_task_set):
    """T2: R = C2 + ceil(R/T1) * C1 = 2 + 1*1 = 3"""
    tasks = assign_rm_priorities(classic_task_set)
    t2 = tasks[1]
    higher = [tasks[0]]
    r = response_time_analysis(t2, higher)
    assert r <= t2.deadline


# ============================================================
# Simulation Tests
# ============================================================

def test_simulate_rm_runs(classic_task_set):
    """محاكاة RM تعمل بدون أخطاء"""
    result = simulate_rm(classic_task_set, until=20)
    assert result.total_time == 20
    assert result.context_switches > 0


def test_simulate_edf_runs(classic_task_set):
    """محاكاة EDF تعمل بدون أخطاء"""
    result = simulate_edf(classic_task_set, until=20)
    assert result.total_time == 20
    assert result.context_switches > 0


def test_rm_no_deadline_misses(classic_task_set):
    """مجموعة قابلة للجدولة → لا deadline misses"""
    result = simulate_rm(classic_task_set, until=20)
    assert result.deadline_misses == 0


def test_edf_no_deadline_misses(classic_task_set):
    result = simulate_edf(classic_task_set, until=20)
    assert result.deadline_misses == 0