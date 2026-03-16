import logging
from datetime import datetime
from typing import Literal, Optional

import asyncpg

from models.db import CryptoPrice, PriceAlert, StockPrice

logger = logging.getLogger(__name__)

# Latest price per coin — DISTINCT ON picks the newest row per symbol
_LATEST_PRICES_SQL = """
    SELECT DISTINCT ON (symbol)
        symbol, name, price_usd, market_cap, volume_24h, price_change_24h, timestamp
    FROM crypto_prices
    ORDER BY symbol, timestamp DESC
"""

# Raw history rows for a symbol in a time range, newest first, capped at 1000
_HISTORY_RAW_SQL = """
    SELECT symbol, name, price_usd, market_cap, volume_24h, price_change_24h, timestamp
    FROM crypto_prices
    WHERE symbol = $1 AND timestamp BETWEEN $2 AND $3
    ORDER BY timestamp ASC
    LIMIT 1000
"""

# Time-bucketed history — one pre-built SQL constant per supported interval.
# Using string .format() to splice an interval string into SQL looks alarming even
# though the value is not user-supplied; separate constants remove the ambiguity.
_HISTORY_BUCKETED_1H_SQL = """
    SELECT
        symbol,
        MAX(name)                                  AS name,
        AVG(price_usd)                             AS price_usd,
        AVG(market_cap)                            AS market_cap,
        AVG(volume_24h)                            AS volume_24h,
        AVG(price_change_24h)                      AS price_change_24h,
        time_bucket('1 hour'::interval, timestamp) AS timestamp
    FROM crypto_prices
    WHERE symbol = $1 AND timestamp BETWEEN $2 AND $3
    GROUP BY symbol, time_bucket('1 hour'::interval, timestamp)
    ORDER BY timestamp ASC
"""

_HISTORY_BUCKETED_1D_SQL = """
    SELECT
        symbol,
        MAX(name)                                 AS name,
        AVG(price_usd)                            AS price_usd,
        AVG(market_cap)                           AS market_cap,
        AVG(volume_24h)                           AS volume_24h,
        AVG(price_change_24h)                     AS price_change_24h,
        time_bucket('1 day'::interval, timestamp) AS timestamp
    FROM crypto_prices
    WHERE symbol = $1 AND timestamp BETWEEN $2 AND $3
    GROUP BY symbol, time_bucket('1 day'::interval, timestamp)
    ORDER BY timestamp ASC
"""

# ---------------------------------------------------------------------------
# Stock queries — mirror the crypto queries against stock_prices table
# ---------------------------------------------------------------------------

_LATEST_STOCKS_SQL = """
    SELECT DISTINCT ON (symbol)
        symbol, name, price_usd, market_cap, volume_24h, price_change_24h, timestamp
    FROM stock_prices
    ORDER BY symbol, timestamp DESC
"""

_STOCK_HISTORY_RAW_SQL = """
    SELECT symbol, name, price_usd, market_cap, volume_24h, price_change_24h, timestamp
    FROM stock_prices
    WHERE symbol = $1 AND timestamp BETWEEN $2 AND $3
    ORDER BY timestamp ASC
    LIMIT 1000
"""

_STOCK_HISTORY_BUCKETED_1H_SQL = """
    SELECT
        symbol,
        MAX(name)                                  AS name,
        AVG(price_usd)                             AS price_usd,
        AVG(market_cap)                            AS market_cap,
        AVG(volume_24h)                            AS volume_24h,
        AVG(price_change_24h)                      AS price_change_24h,
        time_bucket('1 hour'::interval, timestamp) AS timestamp
    FROM stock_prices
    WHERE symbol = $1 AND timestamp BETWEEN $2 AND $3
    GROUP BY symbol, time_bucket('1 hour'::interval, timestamp)
    ORDER BY timestamp ASC
"""

_STOCK_HISTORY_BUCKETED_1D_SQL = """
    SELECT
        symbol,
        MAX(name)                                 AS name,
        AVG(price_usd)                            AS price_usd,
        AVG(market_cap)                           AS market_cap,
        AVG(volume_24h)                           AS volume_24h,
        AVG(price_change_24h)                     AS price_change_24h,
        time_bucket('1 day'::interval, timestamp) AS timestamp
    FROM stock_prices
    WHERE symbol = $1 AND timestamp BETWEEN $2 AND $3
    GROUP BY symbol, time_bucket('1 day'::interval, timestamp)
    ORDER BY timestamp ASC
"""

_CREATE_ALERT_SQL = """
    INSERT INTO price_alerts (symbol, target_price, direction)
    VALUES ($1, $2, $3)
    RETURNING id, symbol, target_price, direction, triggered, created_at, triggered_at
"""

_GET_ALERTS_SQL = """
    SELECT id, symbol, target_price, direction, triggered, created_at, triggered_at
    FROM price_alerts
    ORDER BY created_at DESC
"""

_DELETE_ALERT_SQL = """
    DELETE FROM price_alerts WHERE id = $1 RETURNING id
"""

_GET_TRIGGERED_ALERTS_SQL = """
    SELECT id, symbol, target_price, direction, triggered, created_at, triggered_at
    FROM price_alerts
    WHERE triggered = TRUE
    ORDER BY triggered_at DESC
"""


async def get_latest_prices(pool: asyncpg.Pool) -> list[CryptoPrice]:
    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch(_LATEST_PRICES_SQL)
        return [CryptoPrice(**dict(row)) for row in rows]
    except Exception as e:
        logger.error("get_latest_prices failed: %s", e)
        raise


async def get_price_history(
    pool: asyncpg.Pool,
    symbol: str,
    from_time: datetime,
    to_time: datetime,
    interval: Optional[str] = None,
) -> list[CryptoPrice]:
    try:
        async with pool.acquire() as conn:
            if interval == "1h":
                sql = _HISTORY_BUCKETED_1H_SQL
            elif interval == "1d":
                sql = _HISTORY_BUCKETED_1D_SQL
            else:
                sql = _HISTORY_RAW_SQL

            rows = await conn.fetch(sql, symbol, from_time, to_time)
        return [CryptoPrice(**dict(row)) for row in rows]
    except Exception as e:
        logger.error(
            "get_price_history failed for %s [%s → %s]: %s", symbol, from_time, to_time, e
        )
        raise


async def create_alert(
    pool: asyncpg.Pool,
    symbol: str,
    target_price: float,
    direction: Literal["above", "below"],
) -> PriceAlert:
    try:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(_CREATE_ALERT_SQL, symbol, target_price, direction)
        return PriceAlert(**dict(row))
    except Exception as e:
        logger.error("create_alert failed for %s: %s", symbol, e)
        raise


async def get_alerts(pool: asyncpg.Pool) -> list[PriceAlert]:
    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch(_GET_ALERTS_SQL)
        return [PriceAlert(**dict(row)) for row in rows]
    except Exception as e:
        logger.error("get_alerts failed: %s", e)
        raise


async def get_triggered_alerts(pool: asyncpg.Pool) -> list[PriceAlert]:
    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch(_GET_TRIGGERED_ALERTS_SQL)
        return [PriceAlert(**dict(row)) for row in rows]
    except Exception as e:
        logger.error("get_triggered_alerts failed: %s", e)
        raise


async def delete_alert(pool: asyncpg.Pool, alert_id: int) -> bool:
    """Returns True if a row was deleted, False if the id was not found."""
    try:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(_DELETE_ALERT_SQL, alert_id)
        return row is not None
    except Exception as e:
        logger.error("delete_alert failed for id=%d: %s", alert_id, e)
        raise


# ---------------------------------------------------------------------------
# Stock data accessors
# ---------------------------------------------------------------------------

async def get_latest_stocks(pool: asyncpg.Pool) -> list[StockPrice]:
    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch(_LATEST_STOCKS_SQL)
        return [StockPrice(**dict(row)) for row in rows]
    except Exception as e:
        logger.error("get_latest_stocks failed: %s", e)
        raise


async def get_stock_history(
    pool: asyncpg.Pool,
    symbol: str,
    from_time: datetime,
    to_time: datetime,
    interval: Optional[str] = None,
) -> list[StockPrice]:
    try:
        async with pool.acquire() as conn:
            if interval == "1h":
                sql = _STOCK_HISTORY_BUCKETED_1H_SQL
            elif interval == "1d":
                sql = _STOCK_HISTORY_BUCKETED_1D_SQL
            else:
                sql = _STOCK_HISTORY_RAW_SQL

            rows = await conn.fetch(sql, symbol, from_time, to_time)
        return [StockPrice(**dict(row)) for row in rows]
    except Exception as e:
        logger.error(
            "get_stock_history failed for %s [%s → %s]: %s", symbol, from_time, to_time, e
        )
        raise
