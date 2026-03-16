-- MarketPulse — Stock prices hypertable
-- Run after: 001_init.sql

CREATE TABLE IF NOT EXISTS stock_prices (
    symbol           TEXT           NOT NULL,
    name             TEXT           NOT NULL,
    price_usd        NUMERIC(20, 8) NOT NULL,
    market_cap       BIGINT,
    volume_24h       BIGINT,
    price_change_24h NUMERIC(10, 4),
    timestamp        TIMESTAMPTZ    NOT NULL,
    PRIMARY KEY (symbol, timestamp)
);

SELECT create_hypertable(
    'stock_prices',
    'timestamp',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists       => TRUE
);

CREATE INDEX IF NOT EXISTS idx_stock_prices_symbol_time
    ON stock_prices (symbol, timestamp DESC);
