import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.client import BinanceClient
from app.database import get_db
from app.models import Symbol
from app.service import DataIngestionService

queue = asyncio.Queue(maxsize=1024)


@asynccontextmanager
async def lifespan(app: FastAPI):
    db_gen = get_db()
    db = next(db_gen)

    client = BinanceClient(list(Symbol), queue)
    ingestor = DataIngestionService(queue, db)

    producer_task = asyncio.create_task(client.listen())
    consumer_task = asyncio.create_task(ingestor.start_processing())

    yield

    producer_task.cancel()
    consumer_task.cancel()

    try:
        await asyncio.gather(producer_task, consumer_task)
    except asyncio.CancelledError:
        pass
    finally:
        db_gen.close()


app = FastAPI(lifespan=lifespan)
