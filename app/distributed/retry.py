"""
Retry Logic
===========
إعادة محاولة تنفيذ المهام مع Exponential Backoff
"""
import asyncio
import random
from typing import Callable, Awaitable, TypeVar, Optional
from dataclasses import dataclass


T = TypeVar("T")


@dataclass
class RetryPolicy:
    """سياسة إعادة المحاولة"""
    max_attempts: int = 3          # عدد المحاولات
    base_delay: float = 1.0        # تأخير أساسي (ثواني)
    max_delay: float = 30.0        # أقصى تأخير
    exponential_base: float = 2.0  # مضاعف Exponential
    jitter: bool = True            # إضافة عشوائية (تجنب thundering herd)


def calculate_delay(policy: RetryPolicy, attempt: int) -> float:
    """
    يحسب التأخير قبل المحاولة التالية.
    
    delay = min(base * exp_base^(attempt-1), max_delay)
    + jitter (عشوائي 0-1 ثانية)
    """
    delay = policy.base_delay * (policy.exponential_base ** (attempt - 1))
    delay = min(delay, policy.max_delay)
    if policy.jitter:
        delay += random.uniform(0, 1.0)
    return delay


async def retry_async(
    func: Callable[[], Awaitable[T]],
    policy: Optional[RetryPolicy] = None,
    on_retry: Optional[Callable[[int, Exception], None]] = None,
) -> T:
    """
    ينفّذ `func` مع إعادة محاولة عند الفشل.
    
    :param func: دالة async بدون arguments
    :param policy: سياسة إعادة المحاولة
    :param on_retry: callback عند كل فشل (attempt, exception)
    :raises: آخر exception إذا فشلت كل المحاولات
    """
    policy = policy or RetryPolicy()
    last_exc: Optional[Exception] = None

    for attempt in range(1, policy.max_attempts + 1):
        try:
            return await func()
        except Exception as e:
            last_exc = e
            if attempt >= policy.max_attempts:
                break
            if on_retry:
                on_retry(attempt, e)
            delay = calculate_delay(policy, attempt)
            await asyncio.sleep(delay)

    # إذا وصلنا هون، كل المحاولات فشلت
    raise last_exc  # type: ignore