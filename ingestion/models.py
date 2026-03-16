from pydantic import BaseModel
from typing import Optional


class CoinGeckoPrice(BaseModel):
    id: str
    symbol: str
    name: str
    current_price: Optional[float] = None
    market_cap: Optional[float] = None
    total_volume: Optional[float] = None
    price_change_percentage_24h: Optional[float] = None
    last_updated: str
