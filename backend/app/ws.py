"""WebSocket connection manager — one socket per session, server pushes events."""
import asyncio
import time
from typing import Dict
from fastapi import WebSocket


class WSManager:
    def __init__(self):
        self._conns: Dict[str, WebSocket] = {}
        self._lock = asyncio.Lock()

    async def connect(self, sid: str, ws: WebSocket):
        await ws.accept()
        async with self._lock:
            self._conns[sid] = ws

    async def disconnect(self, sid: str):
        async with self._lock:
            self._conns.pop(sid, None)

    async def send(self, sid: str, type_: str, room: str = "", **payload):
        ws = self._conns.get(sid)
        if not ws:
            return
        msg = {"type": type_, "room": room, "ts": time.time(), "payload": payload}
        try:
            await ws.send_json(msg)
        except Exception:
            await self.disconnect(sid)


manager = WSManager()
