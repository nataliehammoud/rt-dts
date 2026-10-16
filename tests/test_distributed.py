"""
Unit Tests for Distributed Components
======================================
"""
import pytest
from app.distributed.hashing import ConsistentHashRing
from app.distributed.retry import RetryPolicy, calculate_delay


# ============================================================
# Consistent Hashing Tests
# ============================================================

def test_empty_ring():
    """حلقة فاضية ترجع None"""
    ring = ConsistentHashRing()
    assert ring.get_worker("task-1") is None
    assert ring.size == 0


def test_single_worker():
    """Worker واحد → كل المهام عليه"""
    ring = ConsistentHashRing()
    ring.add_worker("worker-1")
    assert ring.get_worker("task-1") == "worker-1"
    assert ring.get_worker("task-2") == "worker-1"
    assert ring.get_worker("anything") == "worker-1"


def test_multiple_workers():
    """3 Workers → المهام تتوزع"""
    ring = ConsistentHashRing(replicas=100)
    for w in ["worker-1", "worker-2", "worker-3"]:
        ring.add_worker(w)

    assignments = set()
    for i in range(100):
        worker = ring.get_worker(f"task-{i}")
        assignments.add(worker)

    # لازم يكون في أكثر من worker
    assert len(assignments) >= 2
    assert ring.size == 3


def test_deterministic():
    """نفس المفتاح → نفس الـ Worker دائمًا"""
    ring = ConsistentHashRing()
    for w in ["a", "b", "c"]:
        ring.add_worker(w)

    w1 = ring.get_worker("my-task")
    w2 = ring.get_worker("my-task")
    assert w1 == w2


def test_remove_worker():
    """حذف Worker → المهام تتوزع على الباقي"""
    ring = ConsistentHashRing()
    ring.add_worker("worker-1")
    ring.add_worker("worker-2")
    ring.add_worker("worker-3")

    ring.remove_worker("worker-2")

    assert ring.size == 2
    for i in range(50):
        worker = ring.get_worker(f"task-{i}")
        assert worker in ["worker-1", "worker-3"]


def test_add_duplicate_worker():
    """إضافة Worker مرتين → ما يأثر"""
    ring = ConsistentHashRing()
    ring.add_worker("worker-1")
    ring.add_worker("worker-1")
    assert ring.size == 1


def test_minimal_reshuffling():
    """
    عند إضافة worker، فقط ~1/N من المهام تنتقل.
    هاد أهم ميزة في Consistent Hashing.
    """
    ring = ConsistentHashRing(replicas=100)
    for w in ["w1", "w2", "w3"]:
        ring.add_worker(w)

    # خزّن التوزيع الأصلي
    original = {f"task-{i}": ring.get_worker(f"task-{i}") for i in range(1000)}

    # أضف worker جديد
    ring.add_worker("w4")

    # احسب كم مهمة انتقلت
    moved = sum(
        1 for i in range(1000)
        if ring.get_worker(f"task-{i}") != original[f"task-{i}"]
    )

    # المفروض ~25% (1/4) — نسمح 15-35%
    assert 150 < moved < 350, f"Moved: {moved} (expected ~250)"


# ============================================================
# Retry Logic Tests
# ============================================================

def test_retry_policy_defaults():
    policy = RetryPolicy()
    assert policy.max_attempts == 3
    assert policy.base_delay == 1.0


def test_calculate_delay_exponential():
    """التأخير يزيد exponentially"""
    policy = RetryPolicy(base_delay=1.0, exponential_base=2.0, jitter=False)

    assert calculate_delay(policy, 1) == 1.0   # 1 * 2^0
    assert calculate_delay(policy, 2) == 2.0   # 1 * 2^1
    assert calculate_delay(policy, 3) == 4.0   # 1 * 2^2
    assert calculate_delay(policy, 4) == 8.0   # 1 * 2^3


def test_calculate_delay_max_cap():
    """التأخير ما يتجاوز max_delay"""
    policy = RetryPolicy(base_delay=1.0, exponential_base=2.0, max_delay=5.0, jitter=False)
    assert calculate_delay(policy, 10) == 5.0


def test_calculate_delay_with_jitter():
    """مع jitter، التأخير مختلف"""
    policy = RetryPolicy(base_delay=1.0, jitter=True)
    delays = [calculate_delay(policy, 1) for _ in range(10)]
    # المفروض كلهم بين 1.0 و 2.0
    assert all(1.0 <= d <= 2.0 for d in delays)
    # المفروض مش كلهم متطابقين (jitter)
    assert len(set(delays)) > 1