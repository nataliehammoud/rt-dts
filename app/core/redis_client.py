"""
Redis Client
============
اتصال Redis مشترك لكل المشروع
"""
import redis.asyncio as aioredis
from app.core.config import settings


# Connection Pool مشترك
redis_client: aioredis.Redis = aioredis.from_url(
    settings.redis_url,
    encoding="utf-8",
    decode_responses=True,
)


async def get_redis() -> aioredis.Redis:
    """يرجع اتصال Redis"""
    return redis_client


async def close_redis():
    """إغلاق الاتصال عند الإطفاء"""
    await redis_client.close()