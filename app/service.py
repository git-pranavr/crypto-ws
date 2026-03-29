import asyncio
from datetime import datetime, timezone

import orjson
from sqlalchemy.orm.session import Session

from app.models import PriceChange, Symbol


class DataIngestionService:
    def __init__(self, queue: asyncio.Queue, db: Session) -> None:
        self.queue = queue
        self.db = db

    async def start_processing(self):
        while True:
            await self._process_next()

    async def _process_next(self):
        message = await self.queue.get()
        await self._save_record(message)
        self.queue.task_done()

    async def _save_record(self, message):
        try:
            data = orjson.loads(message.data)
            row = PriceChange(
                symbol=Symbol.from_str(data["s"]),
                last_price=float(data["c"]),
                change_percentage_24h=float(data["P"]),
                timestamp=datetime.fromtimestamp(data["E"] / 1000, tz=timezone.utc),
            )
            self.db.add(row)
            self.db.commit()
        except Exception as e:
            print(e)
