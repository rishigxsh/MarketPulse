"""
Background ingestion service — runs inside the FastAPI process.

Fetches crypto prices from CoinGecko and stock quotes from Finnhub every
FETCH_INTERVAL_SECONDS and writes directly to the DB. Bypasses Redis queue.
"""

import logging
from datetime import datetime, timezone

import asyncpg
import httpx

from config import settings

logger = logging.getLogger(__name__)

CRYPTO_INSERT_SQL = """
    INSERT INTO crypto_prices (symbol, name, price_usd, market_cap, volume_24h, price_change_24h, timestamp)
    VALUES ($1, $2, $3, $4, $5, $6, $7)
    ON CONFLICT (symbol, timestamp) DO NOTHING
"""

STOCK_INSERT_SQL = """
    INSERT INTO stock_prices (symbol, name, price_usd, market_cap, volume_24h, price_change_24h, timestamp)
    VALUES ($1, $2, $3, $4, $5, $6, $7)
    ON CONFLICT (symbol, timestamp) DO NOTHING
"""

STOCKS: dict[str, str] = {
    "AAPL": "Apple", "MSFT": "Microsoft", "GOOGL": "Alphabet", "AMZN": "Amazon",
    "NVDA": "NVIDIA", "META": "Meta Platforms", "TSLA": "Tesla", "JPM": "JPMorgan Chase",
    "V": "Visa", "JNJ": "Johnson & Johnson", "WMT": "Walmart", "PG": "Procter & Gamble",
    "MA": "Mastercard", "UNH": "UnitedHealth", "HD": "Home Depot", "DIS": "Walt Disney",
    "BAC": "Bank of America", "ADBE": "Adobe", "CRM": "Salesforce", "NFLX": "Netflix",
    "AMD": "AMD", "INTC": "Intel", "PYPL": "PayPal", "CSCO": "Cisco", "KO": "Coca-Cola",
}


async def _fetch_crypto(client: httpx.AsyncClient) -> list[tuple]:
    try:
        resp = await client.get(
            f"{settings.coingecko_base_url}/coins/markets",
            params={"vs_currency": "usd", "order": "market_cap_desc", "per_page": 50, "page": 1},
        )
        resp.raise_for_status()
        rows = []
        for coin in resp.json():
            ts_raw = coin.get("last_updated")
            try:
                ts = datetime.fromisoformat(ts_raw.replace("Z", "+00:00")) if ts_raw else datetime.now(timezone.utc)
            except Exception:
                ts = datetime.now(timezone.utc)
            rows.append((
                coin["symbol"],
                coin["name"],
                float(coin["current_price"]) if coin.get("current_price") else 0.0,
                coin.get("market_cap"),
                coin.get("total_volume"),
                float(coin["price_change_percentage_24h"]) if coin.get("price_change_percentage_24h") else None,
                ts,
            ))
        logger.info("Fetched %d crypto prices", len(rows))
        return rows
    except Exception as e:
        logger.error("Failed to fetch crypto prices: %s", e)
        return []


async def _fetch_stocks(client: httpx.AsyncClient) -> list[tuple]:
    if not settings.finnhub_api_key:
        return []
    rows = []
    ts = datetime.now(timezone.utc)
    for symbol, name in STOCKS.items():
        try:
            resp = await client.get(
                "https://finnhub.io/api/v1/quote",
                params={"symbol": symbol, "token": settings.finnhub_api_key},
            )
            resp.raise_for_status()
            data = resp.json()
            if data.get("c"):
                rows.append((
                    symbol.lower(),
                    name,
                    float(data["c"]),
                    None,
                    None,
                    float(data["dp"]) if data.get("dp") else None,
                    ts,
                ))
        except Exception as e:
            logger.error("Failed to fetch stock %s: %s", symbol, e)
    logger.info("Fetched %d stock quotes", len(rows))
    return rows


async def run_ingestion_cycle(pool: asyncpg.Pool) -> None:
    async with httpx.AsyncClient(timeout=10) as client:
        crypto_rows = await _fetch_crypto(client)
        stock_rows = await _fetch_stocks(client)

    async with pool.acquire() as conn:
        if crypto_rows:
            await conn.executemany(CRYPTO_INSERT_SQL, crypto_rows)
            logger.info("Wrote %d crypto records to DB", len(crypto_rows))
        if stock_rows:
            await conn.executemany(STOCK_INSERT_SQL, stock_rows)
            logger.info("Wrote %d stock records to DB", len(stock_rows))
