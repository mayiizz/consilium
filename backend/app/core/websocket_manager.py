import json
from typing import Dict, Set

from fastapi import WebSocket


class ConnectionManager:
    def __init__(self) -> None:
        self._rooms: Dict[str, Set[WebSocket]] = {}

    async def connect(self, meeting_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        self.register(meeting_id, websocket)

    def register(self, meeting_id: str, websocket: WebSocket) -> None:
        """Add an already-accepted websocket to a meeting room."""
        self._rooms.setdefault(meeting_id, set()).add(websocket)

    def disconnect(self, meeting_id: str, websocket: WebSocket) -> None:
        room = self._rooms.get(meeting_id)
        if room:
            room.discard(websocket)
            if not room:
                del self._rooms[meeting_id]

    async def broadcast(self, meeting_id: str, message: dict) -> None:
        room = self._rooms.get(meeting_id, set())
        dead: Set[WebSocket] = set()
        payload = json.dumps(message)
        for ws in room:
            try:
                await ws.send_text(payload)
            except Exception:
                dead.add(ws)
        for ws in dead:
            self.disconnect(meeting_id, ws)

    def count(self, meeting_id: str) -> int:
        return len(self._rooms.get(meeting_id, set()))


ws_manager = ConnectionManager()
