from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel


class CryptoPrice(BaseModel):
    symbol: str
    name: str
    price_usd: float
    market_cap: Optional[float] = None
    volume_24h: Optional[float] = None
    price_change_24h: Optional[float] = None
    timestamp: datetime


class StockPrice(BaseModel):
    symbol: str
    name: str
    price_usd: float
    market_cap: Optional[float] = None
    volume_24h: Optional[float] = None
    price_change_24h: Optional[float] = None
    timestamp: datetime


class PriceAlert(BaseModel):
    id: int
    symbol: str
    target_price: float
    direction: Literal["above", "below"]
    triggered: bool
    created_at: datetime
    triggered_at: Optional[datetime] = None
