from fastapi import WebSocket #type:ignore


class ConnectionManager:
    """Tracks active WebSocket connections per user for multi-client broadcasting."""

    def __init__(self):
        # user_id -> list of active connections (agent + dashboard, etc.)
        self.active_connections: dict[str, list[WebSocket]] = {}

    def connect(self, user_id: str, websocket: WebSocket):
        self.active_connections.setdefault(user_id, []).append(websocket)

    def disconnect(self, user_id: str, websocket: WebSocket):
        if user_id in self.active_connections:
            if websocket in self.active_connections[user_id]:
                self.active_connections[user_id].remove(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]

    async def broadcast(self, user_id: str, message: dict):
        """Send a message to all connections for this user (agent + dashboard)."""
        for connection in self.active_connections.get(user_id, []):
            try:
                await connection.send_json(message)
            except Exception:
                pass


manager = ConnectionManager()