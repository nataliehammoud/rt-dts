"""
Run ETL once — للاختبار اليدوي
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.redis_client import redis_client, close_redis
from app.warehouse.etl import run_etl_once


async def main():
    stats = await run_etl_once(redis_client)
    print("ETL stats:", stats)
    await close_redis()


if __name__ == "__main__":
    asyncio.run(main())