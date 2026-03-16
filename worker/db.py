import logging
import asyncpg
from models import PriceRecord

logger = logging.getLogger(__name__)

INSERT_CRYPTO_SQL = """
    INSERT INTO crypto_prices (symbol, name, price_usd, market_cap, volume_24h, price_change_24h, timestamp)
    VALUES ($1, $2, $3, $4, $5, $6, $7)
    ON CONFLICT (symbol, timestamp) DO NOTHING
"""

INSERT_STOCK_SQL = """
    INSERT INTO stock_prices (symbol, name, price_usd, market_cap, volume_24h, price_change_24h, timestamp)
    VALUES ($1, $2, $3, $4, $5, $6, $7)
    ON CONFLICT (symbol, timestamp) DO NOTHING
"""


async def write_price(pool: asyncpg.Pool, record: PriceRecord, table: str = "crypto") -> None:
    sql = INSERT_STOCK_SQL if table == "stock" else INSERT_CRYPTO_SQL
    try:
        async with pool.acquire() as conn:
            await conn.execute(
                sql,
                record.symbol,
                record.name,
                record.price_usd,
                record.market_cap,
                record.volume_24h,
                record.price_change_24h,
                record.timestamp,
            )
        logger.info("Wrote %s record: %s @ %s", table, record.symbol.upper(), record.price_usd)
    except Exception as e:
        logger.error(
            "Failed to write %s record for %s at %s: %s",
            table,
            record.symbol,
            record.timestamp,
            e,
        )
