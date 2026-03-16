"""
Backfill historical stock price data from Yahoo Finance into the stock_prices table.

Fetches 30 days of hourly data for each tracked stock and inserts directly
into TimescaleDB. Safe to re-run — uses ON CONFLICT DO NOTHING.

Usage:
    docker compose exec ingestion python backfill_stocks.py
    # or locally:
    python backfill_stocks.py
"""

import asyncio
import logging
import os
from datetime import datetime, timezone

import asyncpg
import yfinance as yf

from stock_fetcher import STOCKS

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("backfill")

INSERT_SQL = """
    INSERT INTO stock_prices (symbol, name, price_usd, market_cap, volume_24h, price_change_24h, timestamp)
    VALUES ($1, $2, $3, $4, $5, $6, $7)
    ON CONFLICT (symbol, timestamp) DO NOTHING
"""


def fetch_history(symbol: str, period: str = "30d", interval: str = "1h"):
    """Fetch historical data from Yahoo Finance. Returns a pandas DataFrame."""
    ticker = yf.Ticker(symbol)
    df = ticker.history(period=period, interval=interval)
    return df


async def backfill(period: str = "30d", interval: str = "1h") -> None:
    postgres_host = os.environ.get("POSTGRES_HOST", "localhost")
    postgres_port = int(os.environ.get("POSTGRES_PORT", "5432"))
    postgres_db = os.environ.get("POSTGRES_DB", "marketpulse")
    postgres_user = os.environ.get("POSTGRES_USER", "marketpulse")
    postgres_password = os.environ.get("POSTGRES_PASSWORD", "marketpulse123")

    dsn = f"postgresql://{postgres_user}:{postgres_password}@{postgres_host}:{postgres_port}/{postgres_db}"

    pool = await asyncpg.create_pool(dsn, min_size=2, max_size=5)
    logger.info("Connected to TimescaleDB")

    total_inserted = 0

    for symbol, name in STOCKS.items():
        logger.info("Fetching %s history for %s (%s)...", period, symbol, name)
        try:
            df = await asyncio.to_thread(fetch_history, symbol, period, interval)
        except Exception as e:
            logger.error("Failed to fetch %s: %s", symbol, e)
            continue

        if df.empty:
            logger.warning("No data returned for %s", symbol)
            continue

        rows = []
        for idx, row in df.iterrows():
            ts = idx.to_pydatetime()
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            else:
                ts = ts.astimezone(timezone.utc)

            rows.append((
                symbol.lower(),
                name,
                float(row["Close"]),
                None,                           # market_cap
                int(row["Volume"]) if row["Volume"] else None,
                None,                           # price_change_24h
                ts,
            ))

        async with pool.acquire() as conn:
            await conn.executemany(INSERT_SQL, rows)
        total_inserted += len(rows)
        logger.info("Inserted %d records for %s", len(rows), symbol)

    await pool.close()
    logger.info("Backfill complete — %d total records inserted across %d stocks", total_inserted, len(STOCKS))


if __name__ == "__main__":
    asyncio.run(backfill())
