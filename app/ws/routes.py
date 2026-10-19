"""
WebSocket Routes
================
نقاط اتصال WebSocket
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.ws.manager import manager


router = APIRouter()


@router.websocket("/ws/events")
async def websocket_events(websocket: WebSocket):
    """
    WebSocket endpoint للأحداث اللحظية.
    
    الاستخدام من JavaScript:
        const ws = new WebSocket('ws://localhost:8000/ws/events');
        ws.onmessage = (e) => console.log(JSON.parse(e.data));
    """
    await manager.connect(websocket)
    try:
        # أرسل رسالة ترحيب
        await websocket.send_json({
            "type": "welcome",
            "data": {"message": "Connected to RT-DTS events"},
        })

        # ننتظر أي رسالة من الـ client (ping/pong)
        while True:
            _ = await websocket.receive_text()

    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        manager.disconnect(websocket)