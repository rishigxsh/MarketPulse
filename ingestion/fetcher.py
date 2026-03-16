import logging

import httpx

from config import settings
from models import CoinGeckoPrice

logger = logging.getLogger(__name__)

MARKETS_URL = f"{settings.coingecko_base_url}/coins/markets"
MARKETS_PARAMS = {
    "vs_currency": "usd",
    "order": "market_cap_desc",
    "per_page": 50,
    "page": 1,
}


async def fetch_prices(client: httpx.AsyncClient) -> list[CoinGeckoPrice]:
    try:
        response = await client.get(MARKETS_URL, params=MARKETS_PARAMS)
        response.raise_for_status()
        coins = response.json()
        prices = [CoinGeckoPrice(**coin) for coin in coins]
        logger.info("Fetched %d coins from CoinGecko", len(prices))
        return prices
    except httpx.HTTPStatusError as e:
        logger.error(
            "CoinGecko API returned %s: %s", e.response.status_code, e
        )
        return []
    except httpx.RequestError as e:
        logger.error("Network error fetching prices: %s", e)
        return []
    except Exception as e:
        logger.error("Unexpected error fetching prices: %s", e)
        return []
