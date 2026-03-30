import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import Depends, FastAPI, WebSocket, WebSocketDisconnect
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.client import BinanceClient, BinanceConnectionStatus
from app.connections import ConnectionManager
from app.config import settings
from app.crud import get_last_prices
from app.database import AsyncSessionLocal, get_db
from app.models import PriceChange, Symbol
from app.schemas import LastPrice
from app.service import RelayService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

connection_manager = ConnectionManager()
queue = asyncio.Queue(maxsize=1024)

binance_status = BinanceConnectionStatus()
started_at = datetime.now(timezone.utc)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Application startup initiated.")

    async with AsyncSessionLocal() as db:
        client = BinanceClient(
            list(Symbol),
            queue,
            settings.binance_ws_base_urls,
            binance_status,
        )
        relay = RelayService(queue, db, connection_manager.get_active_connections())

        producer_task = asyncio.create_task(client.listen())
        consumer_task = asyncio.create_task(relay.start_processing())
        logger.info("Background tasks started: binance listener and relay processor.")

        yield

        logger.info("Application shutdown initiated.")
        producer_task.cancel()
        consumer_task.cancel()

        try:
            await asyncio.gather(producer_task, consumer_task)
        except asyncio.CancelledError:
            pass
        logger.info("Background tasks stopped.")


app = FastAPI(lifespan=lifespan)


@app.get("/")
async def root():
    return {
        "message": "Service is running.",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    now = datetime.now(timezone.utc)
    database = {"connected": False, "total_price_records": None, "latest_prices": []}

    try:
        await db.execute(text("SELECT 1"))
        total_price_records = await db.scalar(select(func.count()).select_from(PriceChange))
        latest_prices = await get_last_prices(db)
        database = {
            "connected": True,
            "total_price_records": total_price_records,
            "latest_prices": [
                {
                    "symbol": row.symbol.value,
                    "last_price": row.last_price,
                    "change_percentage_24h": row.change_percentage_24h,
                    "timestamp": row.timestamp.isoformat(),
                }
                for row in latest_prices
            ],
        }
    except Exception as exc:
        database["error"] = f"{type(exc).__name__}: {exc}"

    response = {
        "status": "online",
        "started_at": started_at.isoformat(),
        "uptime_seconds": int((now - started_at).total_seconds()),
        "queue_size": queue.qsize(),
        "websocket_clients": len(connection_manager.get_active_connections()),
        "binance": {
            **binance_status.snapshot(),
            "configured_base_urls": settings.binance_ws_base_urls,
        },
        "database": database,
    }
    logger.info(
        "Health check requested. binance_connected=%s queue_size=%s db_connected=%s total_price_records=%s",
        binance_status.connected,
        response["queue_size"],
        database["connected"],
        database["total_price_records"],
    )
    return response


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    if not await connection_manager.connect(websocket):
        return

    try:
        logger.info("Websocket client waiting for inbound message to keep session open.")
        await websocket.receive_text()
    except WebSocketDisconnect:
        connection_manager.disconnect(websocket)
    except Exception:
        logger.exception("Unexpected websocket error")
        connection_manager.disconnect(websocket)


@app.get("/price", response_model=list[LastPrice])
async def get_price(db: AsyncSession = Depends(get_db)):
    prices = await get_last_prices(db)
    logger.info("Price endpoint requested. Returning %s rows.", len(prices))
    return prices
