import asyncio
import json
import logging

import asyncpg
import redis

from config import settings
from db import write_price
from models import PriceRecord

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

CRYPTO_QUEUE_KEY = "marketpulse:prices:queue"
STOCK_QUEUE_KEY = "marketpulse:stocks:queue"
BLPOP_TIMEOUT = 5  # seconds — yields control back to the event loop when queue is empty


def get_redis_client() -> redis.Redis:
    return redis.Redis(
        host=settings.redis_host,
        port=settings.redis_port,
        password=settings.redis_password or None,
        decode_responses=True,
        ssl=settings.redis_ssl,
    )


def deserialize(raw: str) -> PriceRecord | None:
    """Parse a raw JSON message from the queue into a PriceRecord.

    CoinGecko field names differ from our DB column names — map them here.
    Returns None on any parse/validation failure so the worker can skip and continue.
    """
    try:
        data = json.loads(raw)
        return PriceRecord(
            symbol=data["symbol"],
            name=data["name"],
            price_usd=data["current_price"],  # required — KeyError skips this record safely
            market_cap=data.get("market_cap"),
            volume_24h=data.get("total_volume"),
            price_change_24h=data.get("price_change_percentage_24h"),
            timestamp=data["last_updated"],
        )
    except Exception as e:
        logger.error("Failed to deserialize message: %s | raw=%s", e, raw[:200])
        return None


async def consume(pool: asyncpg.Pool, redis_client: redis.Redis) -> None:
    """Main consumer loop — BLPOP from both crypto and stock queues."""
    logger.info(
        "Worker consumer started — listening on '%s' and '%s'",
        CRYPTO_QUEUE_KEY, STOCK_QUEUE_KEY,
    )
    while True:
        try:
            # BLPOP can listen on multiple keys — returns (key, value) or None
            result = await asyncio.to_thread(
                redis_client.blpop,
                [CRYPTO_QUEUE_KEY, STOCK_QUEUE_KEY],
                timeout=BLPOP_TIMEOUT,
            )
            if result is None:
                continue  # timeout — queues empty, loop back

            queue_key, raw = result
            record = deserialize(raw)
            if record is None:
                continue  # bad message — already logged, skip

            table = "stock" if queue_key == STOCK_QUEUE_KEY else "crypto"
            await write_price(pool, record, table)

        except redis.exceptions.ConnectionError as e:
            logger.error("Redis connection lost: %s — retrying in 5s", e)
            await asyncio.sleep(5)
        except Exception as e:
            logger.error("Unexpected error in consumer loop: %s", e)
            await asyncio.sleep(1)


async def main() -> None:
    logger.info("Worker starting up")

    redis_client = get_redis_client()

    # Verify Redis is reachable before creating the DB pool
    try:
        redis_client.ping()
        logger.info("Redis connection OK")
    except redis.exceptions.ConnectionError as e:
        logger.error("Cannot reach Redis at startup: %s", e)
        raise

    pool = await asyncpg.create_pool(
        host=settings.postgres_host,
        port=settings.postgres_port,
        database=settings.postgres_db,
        user=settings.postgres_user,
        password=settings.postgres_password,
        min_size=2,
        max_size=5,
        command_timeout=30,
    )
    logger.info("TimescaleDB connection pool created")

    try:
        await consume(pool, redis_client)
    finally:
        await pool.close()
        redis_client.close()
        logger.info("Worker shut down cleanly")


if __name__ == "__main__":
    asyncio.run(main())
