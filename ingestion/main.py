import asyncio
import logging

import httpx
import redis

from config import settings
from fetcher import fetch_prices
from publisher import publish_prices, publish_stocks
from stock_fetcher import fetch_stock_quotes

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def get_redis_client() -> redis.Redis:
    return redis.Redis(
        host=settings.redis_host,
        port=settings.redis_port,
        password=settings.redis_password or None,
        decode_responses=True,
    )


async def run_cycle(http_client: httpx.AsyncClient, r: redis.Redis) -> None:
    # Crypto
    prices = await fetch_prices(http_client)
    if prices:
        publish_prices(r, prices)
    else:
        logger.warning("No crypto prices fetched — skipping publish for this cycle")

    # Stocks (only if Finnhub API key is configured)
    if settings.finnhub_api_key:
        quotes = await fetch_stock_quotes(http_client)
        if quotes:
            publish_stocks(r, quotes)
        else:
            logger.warning("No stock quotes fetched — skipping publish for this cycle")
    else:
        logger.debug("No FINNHUB_API_KEY set — skipping stock ingestion")


async def main() -> None:
    logger.info(
        "Ingestion starting — fetch interval: %ds", settings.fetch_interval_seconds
    )
    r = get_redis_client()
    async with httpx.AsyncClient(timeout=10) as http_client:
        while True:
            try:
                await run_cycle(http_client, r)
            except Exception as e:
                logger.error("Unhandled error in fetch cycle: %s", e)
            await asyncio.sleep(settings.fetch_interval_seconds)


if __name__ == "__main__":
    asyncio.run(main())
