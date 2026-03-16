import logging
from datetime import datetime, timezone

import asyncpg

from models.db import PriceAlert

logger = logging.getLogger(__name__)

# Latest price per symbol among all tracked coins
_LATEST_PRICE_PER_SYMBOL_SQL = """
    SELECT DISTINCT ON (symbol) symbol, price_usd
    FROM crypto_prices
    ORDER BY symbol, timestamp DESC
"""

# Fetch all untriggered alerts
_UNTRIGGERED_ALERTS_SQL = """
    SELECT id, symbol, target_price, direction, triggered, created_at, triggered_at
    FROM price_alerts
    WHERE triggered = FALSE
"""

# Mark an alert as triggered
_TRIGGER_ALERT_SQL = """
    UPDATE price_alerts
    SET triggered = TRUE, triggered_at = $2
    WHERE id = $1
    RETURNING id, symbol, target_price, direction, triggered, created_at, triggered_at
"""


async def check_alerts(pool: asyncpg.Pool) -> list[PriceAlert]:
    """Check all untriggered alerts against the latest prices.

    Returns the list of alerts that were triggered in this run.
    Errors are logged but never raised — the loop must keep running.
    """
    triggered: list[PriceAlert] = []

    try:
        async with pool.acquire() as conn:
            alert_rows = await conn.fetch(_UNTRIGGERED_ALERTS_SQL)

            if not alert_rows:
                return []

            price_rows = await conn.fetch(_LATEST_PRICE_PER_SYMBOL_SQL)

            # Build a symbol → latest_price lookup
            prices: dict[str, float] = {
                row["symbol"]: float(row["price_usd"]) for row in price_rows
            }

            now = datetime.now(timezone.utc)

            for alert_row in alert_rows:
                symbol = alert_row["symbol"]
                latest_price = prices.get(symbol)

                if latest_price is None:
                    logger.debug("No price data for alert symbol '%s' — skipping", symbol)
                    continue

                target = float(alert_row["target_price"])
                direction = alert_row["direction"]

                should_trigger = (
                    direction == "above" and latest_price >= target
                ) or (
                    direction == "below" and latest_price <= target
                )

                if should_trigger:
                    updated = await conn.fetchrow(_TRIGGER_ALERT_SQL, alert_row["id"], now)
                    alert = PriceAlert(**dict(updated))
                    triggered.append(alert)
                    logger.info(
                        "Alert triggered: id=%d %s %s %.8f (current=%.8f)",
                        alert.id,
                        symbol,
                        direction,
                        target,
                        latest_price,
                    )

    except Exception as e:
        logger.error("check_alerts failed: %s", e)

    return triggered
