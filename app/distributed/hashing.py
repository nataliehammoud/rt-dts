"""
Consistent Hashing
==================
حلقة هاش ثابتة لتوزيع المهام على Workers.
عند إضافة/إزالة Worker، فقط ~1/N من المهام تنتقل.
"""
import hashlib
from bisect import bisect_right
from typing import Optional


class ConsistentHashRing:
    """
    حلقة Consistent Hashing.
    
    - كل Worker له عدة "نقاط افتراضية" (virtual nodes) على الحلقة
    - المفتاح (task_id) → hash → أقرب Worker على الحلقة
    - عند إضافة/إزالة Worker، التأثير محدود
    """

    def __init__(self, replicas: int = 100):
        """
        :param replicas: عدد virtual nodes لكل worker (أكثر = توزيع أفضل)
        """
        self.replicas = replicas
        self._ring: dict[int, str] = {}       # hash → worker_id
        self._sorted_keys: list[int] = []     # مفاتيح مرتبة
        self._workers: set[str] = set()

    def _hash(self, key: str) -> int:
        """يحوّل نص لرقم 32-bit"""
        return int(hashlib.md5(key.encode()).hexdigest(), 16)

    def add_worker(self, worker_id: str):
        """يضيف Worker للحلقة"""
        if worker_id in self._workers:
            return
        self._workers.add(worker_id)
        for i in range(self.replicas):
            key = f"{worker_id}:{i}"
            h = self._hash(key)
            self._ring[h] = worker_id
            self._sorted_keys.append(h)
        self._sorted_keys.sort()

    def remove_worker(self, worker_id: str):
        """يحذف Worker من الحلقة"""
        if worker_id not in self._workers:
            return
        self._workers.discard(worker_id)
        for i in range(self.replicas):
            key = f"{worker_id}:{i}"
            h = self._hash(key)
            self._ring.pop(h, None)
        self._sorted_keys = sorted(self._ring.keys())

    def get_worker(self, task_key: str) -> Optional[str]:
        """
        يرجع الـ Worker المسؤول عن هالمفتاح.
        إذا الحلقة فاضية → None.
        """
        if not self._sorted_keys:
            return None

        h = self._hash(task_key)
        # أول نقطة على الحلقة بعد h
        idx = bisect_right(self._sorted_keys, h)
        if idx == len(self._sorted_keys):
            idx = 0  # wrap around
        return self._ring[self._sorted_keys[idx]]

    @property
    def workers(self) -> list[str]:
        return sorted(self._workers)

    @property
    def size(self) -> int:
        return len(self._workers)