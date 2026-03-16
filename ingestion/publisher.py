import json
import logging

import redis

from models import CoinGeckoPrice

logger = logging.getLogger(__name__)

CRYPTO_QUEUE_KEY = "marketpulse:prices:queue"
STOCK_QUEUE_KEY = "marketpulse:stocks:queue"


def publish_prices(r: redis.Redis, prices: list[CoinGeckoPrice]) -> int:
    if not prices:
        return 0
    try:
        payloads = [price.model_dump_json() for price in prices]
        r.rpush(CRYPTO_QUEUE_KEY, *payloads)
        logger.info("Published %d crypto messages to queue", len(payloads))
        return len(payloads)
    except redis.RedisError as e:
        logger.error("Failed to publish prices to Redis: %s", e)
        return 0
    except Exception as e:
        logger.error("Unexpected error publishing prices: %s", e)
        return 0


def publish_stocks(r: redis.Redis, quotes: list[dict]) -> int:
    if not quotes:
        return 0
    try:
        payloads = [json.dumps(q) for q in quotes]
        r.rpush(STOCK_QUEUE_KEY, *payloads)
        logger.info("Published %d stock messages to queue", len(payloads))
        return len(payloads)
    except redis.RedisError as e:
        logger.error("Failed to publish stocks to Redis: %s", e)
        return 0
    except Exception as e:
        logger.error("Unexpected error publishing stocks: %s", e)
        return 0
