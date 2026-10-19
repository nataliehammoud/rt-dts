"""
Test WebSocket
==============
يتصل بالـ WebSocket endpoint ويستقبل رسالة الترحيب.

Usage:
    python scripts/test_ws.py
"""
import asyncio
import sys
import os
import websockets

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


async def test():
    uri = "ws://localhost:8000/ws/events"
    print(f"Connecting to {uri}...")

    async with websockets.connect(uri) as ws:
        msg = await ws.recv()
        print(f"Received: {msg}")


if __name__ == "__main__":
    asyncio.run(test())