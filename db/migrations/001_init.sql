-- MarketPulse — Phase 2 Database Schema
-- Run after: CREATE EXTENSION IF NOT EXISTS timescaledb;

-- ============================================================
-- crypto_prices — TimescaleDB hypertable for time-series data
-- ============================================================
CREATE TABLE IF NOT EXISTS crypto_prices (
    symbol           TEXT           NOT NULL,
    name             TEXT           NOT NULL,
    price_usd        NUMERIC(20, 8) NOT NULL,
    market_cap       BIGINT,
    volume_24h       BIGINT,
    price_change_24h NUMERIC(10, 4),
    timestamp        TIMESTAMPTZ    NOT NULL,
    -- Composite PK must include the partition column (timestamp)
    PRIMARY KEY (symbol, timestamp)
);

SELECT create_hypertable(
    'crypto_prices',
    'timestamp',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists       => TRUE
);

-- Fast lookups by symbol with newest rows first
CREATE INDEX IF NOT EXISTS idx_crypto_prices_symbol_time
    ON crypto_prices (symbol, timestamp DESC);

-- ============================================================
-- price_alerts — regular table (not time-series, not a hypertable)
-- ============================================================
CREATE TABLE IF NOT EXISTS price_alerts (
    id           SERIAL      PRIMARY KEY,
    symbol       TEXT        NOT NULL,
    target_price NUMERIC(20, 8) NOT NULL,
    direction    TEXT        NOT NULL CHECK (direction IN ('above', 'below')),
    triggered    BOOLEAN     NOT NULL DEFAULT FALSE,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    triggered_at TIMESTAMPTZ
);

-- Fast lookup of all alerts for a given symbol
CREATE INDEX IF NOT EXISTS idx_price_alerts_symbol
    ON price_alerts (symbol);

-- Fast lookup of untriggered alerts (used in alert check loop)
CREATE INDEX IF NOT EXISTS idx_price_alerts_triggered
    ON price_alerts (triggered)
    WHERE triggered = FALSE;
