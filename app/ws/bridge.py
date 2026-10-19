"""
Redis → WebSocket Bridge
=========================
يستمع لقناة Redis Pub/Sub ويبث الأحداث لكل الـ WebSocket clients
"""
import asyncio
import json
from typing import Optional

from app.core.redis_client import redis_client
from app.workers.worker import EVENTS_CHANNEL
from app.ws.manager import manager


_bridge_task: Optional[asyncio.Task] = None


async def _listen_loop():
    """
    يستمع للأحداث من Redis Pub/Sub ويبثها.
    - يعمل في الخلفية
    - يتعامل مع انقطاعات بشكل سلس
    """
    print("🌉 Redis→WebSocket bridge started")
    pubsub = redis_client.pubsub()

    try:
        await pubsub.subscribe(EVENTS_CHANNEL)

        while True:
            try:
                message = await pubsub.get_message(
                    ignore_subscribe_messages=True,
                    timeout=1.0,
                )
                if message is None:
                    continue

                raw = message.get("data")
                if not raw:
                    continue

                try:
                    event = json.loads(raw)
                except json.JSONDecodeError:
                    continue

                # بث للـ WebSocket clients
                await manager.broadcast({
                    "type": "event",
                    "data": event,
                })

            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"🌉 Bridge error: {e}")
                await asyncio.sleep(1)

    finally:
        try:
            await pubsub.unsubscribe(EVENTS_CHANNEL)
            await pubsub.close()
        except Exception:
            pass
        print("🌉 Redis→WebSocket bridge stopped")


async def start_bridge():
    """يبدأ bridge كـ background task"""
    global _bridge_task
    if _bridge_task is None or _bridge_task.done():
        _bridge_task = asyncio.create_task(_listen_loop())


async def stop_bridge():
    """يوقف bridge بشكل نظيف"""
    global _bridge_task
    if _bridge_task and not _bridge_task.done():
        _bridge_task.cancel()
        try:
            await _bridge_task
        except asyncio.CancelledError:
            pass
        _bridge_task = None