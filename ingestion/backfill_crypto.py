"""
Backfill historical crypto price data from CoinGecko into the crypto_prices table.

Fetches 30 days of data for the top 50 coins by market cap and inserts directly
into TimescaleDB. Safe to re-run — uses ON CONFLICT DO NOTHING.

Usage:
    docker compose exec ingestion python backfill_crypto.py
"""

import asyncio
import logging
import os
from datetime import datetime, timezone

import asyncpg
import httpx

from config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("backfill_crypto")

INSERT_SQL = """
    INSERT INTO crypto_prices (symbol, name, price_usd, market_cap, volume_24h, price_change_24h, timestamp)
    VALUES ($1, $2, $3, $4, $5, $6, $7)
    ON CONFLICT (symbol, timestamp) DO NOTHING
"""

# CoinGecko free tier: ~10 calls/min with burst penalties
RATE_LIMIT_DELAY = 8


async def get_top_coins(client: httpx.AsyncClient) -> list[dict]:
    """Fetch top 50 coins from CoinGecko /coins/markets to get IDs and symbols."""
    url = f"{settings.coingecko_base_url}/coins/markets"
    resp = await client.get(url, params={
        "vs_currency": "usd",
        "order": "market_cap_desc",
        "per_page": 50,
        "page": 1,
    })
    resp.raise_for_status()
    return resp.json()


async def fetch_market_chart(
    client: httpx.AsyncClient,
    coin_id: str,
    days: int = 30,
    max_retries: int = 3,
) -> dict | None:
    """Fetch historical price data from CoinGecko /coins/{id}/market_chart."""
    url = f"{settings.coingecko_base_url}/coins/{coin_id}/market_chart"
    for attempt in range(max_retries):
        try:
            resp = await client.get(url, params={
                "vs_currency": "usd",
                "days": days,
            })
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429 and attempt < max_retries - 1:
                wait = 30 * (attempt + 1)
                logger.warning("Rate limited for %s, waiting %ds (attempt %d/%d)", coin_id, wait, attempt + 1, max_retries)
                await asyncio.sleep(wait)
                continue
            logger.error("CoinGecko error for %s: %s", coin_id, e.response.status_code)
            return None
        except Exception as e:
            logger.error("Error fetching chart for %s: %s", coin_id, e)
            return None
    return None


async def backfill(days: int = 30) -> None:
    postgres_host = os.environ.get("POSTGRES_HOST", "localhost")
    postgres_port = int(os.environ.get("POSTGRES_PORT", "5432"))
    postgres_db = os.environ.get("POSTGRES_DB", "marketpulse")
    postgres_user = os.environ.get("POSTGRES_USER", "marketpulse")
    postgres_password = os.environ.get("POSTGRES_PASSWORD", "marketpulse123")

    dsn = f"postgresql://{postgres_user}:{postgres_password}@{postgres_host}:{postgres_port}/{postgres_db}"

    pool = await asyncpg.create_pool(dsn, min_size=2, max_size=5)
    logger.info("Connected to TimescaleDB")

    total_inserted = 0

    async with httpx.AsyncClient(timeout=15) as client:
        # Step 1: Get top 50 coins to know their IDs, symbols, and names
        logger.info("Fetching top 50 coins list...")
        try:
            coins = await get_top_coins(client)
        except Exception as e:
            logger.error("Failed to fetch coin list: %s", e)
            await pool.close()
            return

        logger.info("Got %d coins, starting backfill...", len(coins))
        await asyncio.sleep(RATE_LIMIT_DELAY)

        # Step 2: For each coin, fetch market_chart and insert
        for coin in coins:
            coin_id = coin["id"]
            symbol = coin["symbol"]
            name = coin["name"]

            logger.info("Fetching %d-day chart for %s (%s)...", days, symbol.upper(), name)
            data = await fetch_market_chart(client, coin_id, days)

            if not data or "prices" not in data:
                await asyncio.sleep(RATE_LIMIT_DELAY)
                continue

            prices = data["prices"]            # [[timestamp_ms, price], ...]
            market_caps = data.get("market_caps", [])
            volumes = data.get("total_volumes", [])

            rows = []
            for i, (ts_ms, price) in enumerate(prices):
                ts = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc)
                mcap = int(market_caps[i][1]) if i < len(market_caps) and market_caps[i][1] else None
                vol = int(volumes[i][1]) if i < len(volumes) and volumes[i][1] else None

                rows.append((
                    symbol,
                    name,
                    float(price),
                    mcap,
                    vol,
                    None,       # price_change_24h not available per-point
                    ts,
                ))

            async with pool.acquire() as conn:
                await conn.executemany(INSERT_SQL, rows)
            total_inserted += len(rows)
            logger.info("Inserted %d records for %s", len(rows), symbol.upper())

            await asyncio.sleep(RATE_LIMIT_DELAY)

    await pool.close()
    logger.info("Backfill complete — %d total records inserted across %d coins", total_inserted, len(coins))


if __name__ == "__main__":
    asyncio.run(backfill())
