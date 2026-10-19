"""
WebSocket Connection Manager
=============================
يدير اتصالات WebSocket النشطة ويبث الأحداث لكل الـ clients
"""
from typing import Set
from fastapi import WebSocket
import json


class ConnectionManager:
    """
    مدير الاتصالات:
    - يقبل اتصالات جديدة
    - يبث الأحداث لكل الـ clients المتصلين
    - ينظّف الاتصالات الميتة تلقائيًا
    """

    def __init__(self):
        self.active: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        """يقبل اتصال جديد"""
        await websocket.accept()
        self.active.add(websocket)
        print(f"🔌 WS connected. Total: {len(self.active)}")

    def disconnect(self, websocket: WebSocket):
        """يحذف اتصال"""
        self.active.discard(websocket)
        print(f"🔌 WS disconnected. Total: {len(self.active)}")

    async def broadcast(self, message: dict):
        """
        يبث رسالة لكل الـ clients.
        - أي client يفشل → ينحذف تلقائيًا
        """
        if not self.active:
            return

        text = json.dumps(message, ensure_ascii=False)
        dead = set()

        for ws in list(self.active):
            try:
                await ws.send_text(text)
            except Exception:
                dead.add(ws)

        # تنظيف
        for ws in dead:
            self.disconnect(ws)

    @property
    def count(self) -> int:
        return len(self.active)


# نسخة مشتركة
manager = ConnectionManager()