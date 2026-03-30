import logging

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self, max_connections: int = 1024) -> None:
        self.active_connections: set[WebSocket] = set()
        self.max_connections = max_connections

    def get_active_connections(self):
        return self.active_connections

    async def connect(self, websocket: WebSocket) -> bool:
        if len(self.active_connections) >= self.max_connections:
            logger.warning(
                "Rejecting websocket client: max connections reached (%s)",
                self.max_connections,
            )
            await websocket.close(code=1008)
            return False

        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info(
            "Websocket client connected. Active websocket clients=%s",
            len(self.active_connections),
        )
        return True

    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)
        logger.info(
            "Websocket client disconnected. Active websocket clients=%s",
            len(self.active_connections),
        )
