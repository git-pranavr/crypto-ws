from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, Float
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Symbol(StrEnum):
    BTC = "btcusdt"
    ETH = "ethusdt"
    BNB = "bnbusdt"

    @classmethod
    def from_str(cls, value: str) -> "Symbol":
        return cls(value.lower())


class PriceChange(Base):
    __tablename__ = "price_changes"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    symbol: Mapped[Symbol] = mapped_column(SAEnum(Symbol), nullable=False)
    last_price: Mapped[float] = mapped_column(Float, nullable=False)
    change_percentage_24h: Mapped[float] = mapped_column(Float, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
