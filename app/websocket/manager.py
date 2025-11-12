from typing import Dict, List
from fastapi import WebSocket
import asyncio
import json

class ConnectionManager:
    def __init__(self):
        # map user_id -> set of websockets
        self.active: Dict[str, List[WebSocket]] = {}
        self.lock = asyncio.Lock()

    async def connect(self, user_id: str, websocket: WebSocket):
        await websocket.accept()
        async with self.lock:
            conns = self.active.get(user_id, [])
            conns.append(websocket)
            self.active[user_id] = conns

    async def disconnect(self, user_id: str, websocket: WebSocket):
        async with self.lock:
            conns = self.active.get(user_id, [])
            if websocket in conns:
                conns.remove(websocket)
            if conns:
                self.active[user_id] = conns
            else:
                self.active.pop(user_id, None)

    async def send_personal_message(self, user_id, message: dict):
        conns = self.active.get(str(user_id), [])
        data = json.dumps(message)
        for ws in list(conns):
            try:
                await ws.send_text(data)
            except Exception:
                # ignore broken sockets
                try:
                    await ws.close()
                except Exception:
                    pass

manager = ConnectionManager()
