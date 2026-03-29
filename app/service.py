import asyncio
from datetime import datetime, timezone

import orjson
from fastapi.websockets import WebSocket
from sqlalchemy.orm.session import Session

from app.models import PriceChange, Symbol


class DataIngestionService:
    def __init__(
        self, queue: asyncio.Queue, db: Session, connected: set[WebSocket]
    ) -> None:
        self.queue = queue
        self.db = db
        self.connected = connected

    async def start_processing(self):
        while True:
            try:
                await self._process_next()
            except Exception as e:
                print(e)

    async def _process_next(self):
        message = await self.queue.get()
        data = orjson.loads(message.data)
        processed_data = dict(
            symbol=Symbol.from_str(data["s"]),
            last_price=float(data["c"]),
            change_percentage_24h=float(data["P"]),
            timestamp=datetime.fromtimestamp(data["E"] / 1000, tz=timezone.utc),
        )
        await self._relay(processed_data)
        # await self._save_record(processed_data)
        self.queue.task_done()

    async def _relay(self, data):
        for client in self.connected:
            try:
                await client.send_text(orjson.dumps(data).decode())
            except Exception as e:
                print(e)

    async def _save_record(self, data):
        try:
            self.db.add(PriceChange(**data))
            self.db.commit()
        except Exception as e:
            print(e)
