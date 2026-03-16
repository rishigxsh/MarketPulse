import logging
from datetime import datetime, timezone

import httpx

from config import settings

logger = logging.getLogger(__name__)

QUOTE_URL = "https://finnhub.io/api/v1/quote"

STOCKS: dict[str, str] = {
    "AAPL": "Apple",
    "MSFT": "Microsoft",
    "GOOGL": "Alphabet",
    "AMZN": "Amazon",
    "NVDA": "NVIDIA",
    "META": "Meta Platforms",
    "TSLA": "Tesla",
    "JPM": "JPMorgan Chase",
    "V": "Visa",
    "JNJ": "Johnson & Johnson",
    "WMT": "Walmart",
    "PG": "Procter & Gamble",
    "MA": "Mastercard",
    "UNH": "UnitedHealth",
    "HD": "Home Depot",
    "DIS": "Walt Disney",
    "BAC": "Bank of America",
    "ADBE": "Adobe",
    "CRM": "Salesforce",
    "NFLX": "Netflix",
    "AMD": "AMD",
    "INTC": "Intel",
    "PYPL": "PayPal",
    "CSCO": "Cisco",
    "KO": "Coca-Cola",
}


async def fetch_stock_quotes(client: httpx.AsyncClient) -> list[dict]:
    """Fetch quotes for all tracked stocks from Finnhub. Returns list of dicts
    matching the shape expected by the stock queue consumer."""
    results: list[dict] = []
    now = datetime.now(timezone.utc).isoformat()

    for symbol, name in STOCKS.items():
        try:
            resp = await client.get(
                QUOTE_URL,
                params={"symbol": symbol, "token": settings.finnhub_api_key},
            )
            resp.raise_for_status()
            q = resp.json()

            # Finnhub returns c=0 for invalid/unsupported symbols
            if q.get("c", 0) == 0:
                logger.warning("Finnhub returned 0 price for %s — skipping", symbol)
                continue

            results.append({
                "symbol": symbol.lower(),
                "name": name,
                "current_price": q["c"],
                "market_cap": None,
                "total_volume": None,
                "price_change_percentage_24h": q.get("dp"),
                "last_updated": now,
                "asset_type": "stock",
            })
        except httpx.HTTPStatusError as e:
            logger.error("Finnhub API error for %s: %s %s", symbol, e.response.status_code, e)
        except httpx.RequestError as e:
            logger.error("Network error fetching %s quote: %s", symbol, e)
        except Exception as e:
            logger.error("Unexpected error fetching %s: %s", symbol, e)

    logger.info("Fetched %d stock quotes from Finnhub", len(results))
    return results
