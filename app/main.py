import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from app.client import BinanceClient
from app.database import get_db
from app.models import Symbol
from app.service import DataIngestionService

connected: set[WebSocket] = set()
queue = asyncio.Queue(maxsize=1024)


@asynccontextmanager
async def lifespan(app: FastAPI):
    db_gen = get_db()
    db = next(db_gen)

    client = BinanceClient(list(Symbol), queue)
    ingestor = DataIngestionService(queue, db, connected)

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


@app.get("/health")
async def health_check():
    return {"status": "online", "items_in_queue": queue.qsize()}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connected.add(websocket)
    try:
        await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        connected.discard(websocket)
