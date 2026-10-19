"""
Listen to WebSocket Events
==========================
يستمع لكل الأحداث من WebSocket ويطبعها لحظيًا.

Usage:
    python scripts/listen_ws.py
"""
import asyncio
import sys
import os
import json
import websockets

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


async def listen():
    uri = "ws://localhost:8000/ws/events"
    print(f"🔌 Connecting to {uri}...")
    print("📡 Listening for events (Ctrl+C to stop)...\n")

    async with websockets.connect(uri) as ws:
        async for raw in ws:
            try:
                msg = json.loads(raw)
                event_type = msg.get("type", "?")
                data = msg.get("data", {})

                if event_type == "welcome":
                    print(f"✅ {data.get('message')}")
                elif event_type == "event":
                    ev = data.get("event", "?")
                    worker = data.get("worker_id", "?")
                    task = data.get("task_name", "")
                    print(f"📢 [{worker}] {ev} {task}")
                else:
                    print(f"❓ {msg}")
            except json.JSONDecodeError:
                print(f"📨 {raw}")


if __name__ == "__main__":
    try:
        asyncio.run(listen())
    except KeyboardInterrupt:
        print("\n👋 Stopped.")