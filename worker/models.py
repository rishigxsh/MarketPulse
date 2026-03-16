from datetime import datetime
from typing import Optional

from pydantic import BaseModel, field_validator


class PriceRecord(BaseModel):
    symbol: str
    name: str
    price_usd: float  # NOT NULL in DB — validation fails early if CoinGecko omits this
    market_cap: Optional[float] = None
    volume_24h: Optional[float] = None
    price_change_24h: Optional[float] = None
    timestamp: datetime

    @field_validator("timestamp", mode="before")
    @classmethod
    def parse_timestamp(cls, v: str) -> datetime:
        if isinstance(v, datetime):
            return v
        return datetime.fromisoformat(v.replace("Z", "+00:00"))
