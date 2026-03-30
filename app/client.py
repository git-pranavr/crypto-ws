import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable

from httpx_ws import AsyncWebSocketSession, aconnect_ws

logger = logging.getLogger(__name__)


@dataclass
class BinanceConnectionStatus:
    connected: bool = False
    active_url: str | None = None
    last_message_at: datetime | None = None
    last_connect_attempt_at: datetime | None = None
    last_error: str | None = None
    connect_attempts: int = 0
    successful_connections: int = 0
    message_count: int = 0

    def mark_connecting(self, url: str) -> None:
        self.connected = False
        self.active_url = url
        self.last_connect_attempt_at = datetime.now(timezone.utc)
        self.connect_attempts += 1

    def mark_connected(self, url: str) -> None:
        self.connected = True
        self.active_url = url
        self.last_error = None
        self.successful_connections += 1

    def mark_message_received(self) -> None:
        self.last_message_at = datetime.now(timezone.utc)
        self.message_count += 1

    def mark_error(self, message: str) -> None:
        self.connected = False
        self.last_error = message

    def snapshot(self) -> dict[str, str | bool | None]:
        return {
            "connected": self.connected,
            "active_url": self.active_url,
            "last_connect_attempt_at": self.last_connect_attempt_at.isoformat()
            if self.last_connect_attempt_at
            else None,
            "last_message_at": self.last_message_at.isoformat()
            if self.last_message_at
            else None,
            "last_error": self.last_error,
            "connect_attempts": self.connect_attempts,
            "successful_connections": self.successful_connections,
            "message_count": self.message_count,
        }


class BinanceClient:
    def __init__(
        self,
        symbols: Iterable[str],
        queue: asyncio.Queue,
        base_urls: Iterable[str],
        status: BinanceConnectionStatus,
    ):
        streams = "/".join([f"{s}@ticker" for s in symbols])
        self.urls = [
            f"{base_url.rstrip('/')}/stream?streams={streams}" for base_url in base_urls
        ]
        self.streams = streams
        self.queue = queue
        self.status = status

    async def listen(self):
        logger.info(
            "Starting Binance listener for streams=%s with base_urls=%s",
            self.streams,
            self.urls,
        )
        while True:
            connected = await self._reconnect()
            if not connected:
                logger.warning(
                    "All Binance websocket endpoints failed. Retrying in 5 seconds."
                )
                await asyncio.sleep(5)

    async def _reconnect(self) -> bool:
        for url in self.urls:
            self.status.mark_connecting(url)
            logger.info("Connecting to Binance websocket: %s", url)
            try:
                async with aconnect_ws(url) as conn:
                    self.status.mark_connected(url)
                    logger.info("Connected to Binance websocket: %s", url)
                    await self._receive(conn)
            except Exception as exc:
                message = f"{type(exc).__name__}: {exc}"
                self.status.mark_error(message)
                logger.warning(
                    "Binance websocket connection failed for %s: %s",
                    url,
                    message,
                )
                continue
            logger.warning("Binance websocket connection closed for %s", url)
            return True

        return False

    async def _receive(self, conn: AsyncWebSocketSession):
        while True:
            try:
                message = await conn.receive(timeout=5)
            except TimeoutError:
                logger.debug("Binance websocket receive timeout. Sending ping.")
                await conn.ping()
                continue

            self.status.mark_message_received()
            if self.status.message_count <= 5 or self.status.message_count % 100 == 0:
                logger.info(
                    "Received Binance message #%s. Queue size before enqueue=%s",
                    self.status.message_count,
                    self.queue.qsize(),
                )
            try:
                self.queue.put_nowait(message)
            except asyncio.QueueFull:
                logger.warning(
                    "Market data queue full at size=%s. Dropping oldest message.",
                    self.queue.qsize(),
                )
                self.queue.get_nowait()  # pop oldest
                self.queue.put_nowait(message)
