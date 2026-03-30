import asyncio
import logging
from datetime import datetime, timezone

import orjson
from fastapi.websockets import WebSocket
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import PriceChange, Symbol

logger = logging.getLogger(__name__)


class RelayService:
    def __init__(
        self, queue: asyncio.Queue, db: AsyncSession, connected: set[WebSocket]
    ) -> None:
        self.queue = queue
        self.db = db
        self.connected = connected
        self.processed_messages = 0

    async def start_processing(self):
        logger.info("Starting relay processor.")
        while True:
            try:
                await self._process_next()
            except Exception:
                logger.exception("Failed to process market data message")

    async def _process_next(self):
        message = await self.queue.get()
        try:
            data = orjson.loads(message.data)
            payload = data.get("data", data)
            processed_data = dict(
                symbol=Symbol.from_str(payload["s"]),
                last_price=float(payload["c"]),
                change_percentage_24h=float(payload["P"]),
                timestamp=datetime.fromtimestamp(payload["E"] / 1000, tz=timezone.utc),
            )
            self.processed_messages += 1
            if self.processed_messages <= 5 or self.processed_messages % 100 == 0:
                logger.info(
                    "Processed market data message #%s for symbol=%s price=%s queue_size=%s",
                    self.processed_messages,
                    processed_data["symbol"].value,
                    processed_data["last_price"],
                    self.queue.qsize(),
                )
            await self._relay(processed_data)
            await self._save_record(processed_data)
        finally:
            self.queue.task_done()

    async def _relay(self, data):
        for client in self.connected:
            try:
                await client.send_text(orjson.dumps(data).decode())
            except Exception:
                logger.exception("Failed to relay market data to websocket client")

    async def _save_record(self, data):
        try:
            self.db.add(PriceChange(**data))
            await self.db.commit()
            if self.processed_messages <= 5 or self.processed_messages % 100 == 0:
                logger.info(
                    "Saved market data for symbol=%s timestamp=%s",
                    data["symbol"].value,
                    data["timestamp"].isoformat(),
                )
        except Exception:
            await self.db.rollback()
            logger.exception("Failed to persist market data update")
