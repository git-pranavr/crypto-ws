import asyncio
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from app.client import BinanceClient
from app.connections import ConnectionManager
from app.crud import get_last_prices
from app.database import AsyncSessionLocal, get_db
from app.models import Symbol
from app.schemas import LastPrice
from app.service import RelayService

connection_manager = ConnectionManager()
queue = asyncio.Queue(maxsize=1024)


@asynccontextmanager
async def lifespan(app: FastAPI):

    async with AsyncSessionLocal() as db:
        client = BinanceClient(list(Symbol), queue)
        relay = RelayService(queue, db, connection_manager.get_active_connections())

        producer_task = asyncio.create_task(client.listen())
        consumer_task = asyncio.create_task(relay.start_processing())

        yield

        producer_task.cancel()
        consumer_task.cancel()

        try:
            await asyncio.gather(producer_task, consumer_task)
        except asyncio.CancelledError:
            pass


app = FastAPI(lifespan=lifespan)


@app.get("/health")
async def health_check():
    return {"status": "online"}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    if not await connection_manager.connect(websocket):
        return

    try:
        await websocket.receive_text()
    except WebSocketDisconnect:
        connection_manager.disconnect(websocket)


@app.get("/price", response_model=list[LastPrice])
async def get_price(db: AsyncSession = Depends(get_db)):
    return await get_last_prices(db)
