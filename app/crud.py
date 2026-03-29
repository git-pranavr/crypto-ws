from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import PriceChange


async def get_last_prices(db: AsyncSession):
    result = await db.execute(
        select(PriceChange)
        .distinct(PriceChange.symbol)
        .order_by(PriceChange.symbol, PriceChange.timestamp.desc())
    )
    return result.scalars().all()
