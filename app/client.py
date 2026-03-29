import asyncio
from typing import Iterable

from httpx_ws import AsyncWebSocketSession, aconnect_ws


class BinanceClient:
    def __init__(self, symbols: Iterable[str], queue: asyncio.Queue):
        streams = "/".join([f"{s}@ticker" for s in symbols])
        self.url = f"wss://stream.binance.com:9443/ws/{streams}"
        self.queue = queue

    async def listen(self):
        while True:
            await self._reconnect()

    async def _reconnect(self):
        try:
            async with aconnect_ws(self.url) as conn:
                try:
                    await self._receive(conn)
                except TimeoutError:
                    await conn.ping()
        except Exception:
            await asyncio.sleep(5)

    async def _receive(self, conn: AsyncWebSocketSession):
        message = await conn.receive(timeout=5)

        try:
            self.queue.put_nowait(message)
        except asyncio.QueueFull:
            self.queue.get_nowait()  # pop oldest
            self.queue.put_nowait(message)
