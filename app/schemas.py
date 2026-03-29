from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models import Symbol


class LastPrice(BaseModel):
    symbol: Symbol
    last_price: float
    change_percentage_24h: float
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)
