from fastapi import WebSocket


class ConnectionManager:
    def __init__(self, max_connections: int = 1024) -> None:
        self.active_connections: set[WebSocket] = set()
        self.max_connections = max_connections

    def get_active_connections(self):
        return self.active_connections

    async def connect(self, websocket: WebSocket) -> bool:
        if len(self.active_connections) >= self.max_connections:
            await websocket.close(code=1008)
            return False

        await websocket.accept()
        self.active_connections.add(websocket)
        return True

    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)
