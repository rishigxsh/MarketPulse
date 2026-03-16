import logging
from typing import Optional

import redis.asyncio as aioredis

logger = logging.getLogger(__name__)


async def get_cached(client: aioredis.Redis, key: str) -> Optional[str]:
    try:
        value = await client.get(key)
        if value:
            logger.debug("Cache hit: %s", key)
        return value
    except Exception as e:
        # Cache errors must never break the request — log and return None (cache miss)
        logger.warning("Cache get failed for key '%s': %s", key, e)
        return None


async def set_cached(client: aioredis.Redis, key: str, value: str, ttl: int = 60) -> None:
    try:
        await client.set(key, value, ex=ttl)
        logger.debug("Cache set: %s (ttl=%ds)", key, ttl)
    except Exception as e:
        logger.warning("Cache set failed for key '%s': %s", key, e)
