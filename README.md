# MarketPulse — Real-Time Stock & Crypto Data Pipeline

A full-stack financial data pipeline that ingests real-time cryptocurrency and stock market data, stores it in a time-series database, and visualizes it through an interactive dashboard.

[![Live Demo](https://img.shields.io/badge/Live%20Demo-market--pulse--rouge.vercel.app-brightgreen?logo=vercel)](https://market-pulse-rouge.vercel.app)

![React](https://img.shields.io/badge/React-18-blue?logo=react)
![FastAPI](https://img.shields.io/badge/FastAPI-0.110-green?logo=fastapi)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-blue?logo=postgresql)
![Docker](https://img.shields.io/badge/Docker-Compose-blue?logo=docker)
![License](https://img.shields.io/badge/License-MIT-yellow)

## Architecture

```
CoinGecko API (crypto)     Finnhub API (stocks)
        │                          │
        ▼                          ▼
[ FastAPI Backend — ingestion loop (background task) ]
        │
        ▼
[ PostgreSQL (Supabase) — crypto_prices + stock_prices ]
        │
        ▼
[ FastAPI REST API — /prices/* + /stocks/* + /alerts/* ]
        │
        ▼
[ React + Vite Dashboard ]
```

Data flows strictly in one direction. The backend handles ingestion, storage, and serving.

## Features

- **Real-time price tracking** — 50 cryptocurrencies (CoinGecko) + 25 US stocks (Finnhub)
- **Interactive charts** — 24h, 7d, and 30d price history with Recharts
- **Crypto/Stocks tabs** — separate views with distinct color themes
- **Watchlist** — pin favorite coins with localStorage persistence
- **Price alerts** — set above/below triggers, auto-checked every 30s
- **Time-series storage** — hourly/daily bucketing via PostgreSQL `date_trunc`
- **Redis caching** — 60s TTL on API responses for fast reads
- **Historical backfill** — scripts to populate 30 days of historical data on first deploy

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 18, TypeScript, Vite, Tailwind CSS, Recharts, React Query |
| Backend | FastAPI, asyncpg, Redis, Pydantic |
| Database | PostgreSQL (Supabase) |
| Ingestion | Python, httpx, CoinGecko API, Finnhub API — runs as background task in backend |
| Deployment | Docker Compose (local), Render + Vercel (production) |

## Quick Start

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running
- A free [Finnhub API](https://finnhub.io/) key (optional — stocks disabled without it)

### 1. Clone and configure

```bash
git clone https://github.com/rishigxsh/MarketPulse.git
cd MarketPulse
cp .env.example .env
# Edit .env — fill in your API keys and DB credentials
```

### 2. Start everything

```bash
docker compose up --build -d
```

### 3. Run migrations (first time only)

```bash
docker compose exec postgres psql -U marketpulse -d marketpulse \
  -f /migrations/001_init.sql
docker compose exec postgres psql -U marketpulse -d marketpulse \
  -f /migrations/002_stock_prices.sql
```

### 4. Open the dashboard

- **Dashboard:** http://localhost (nginx, port 80)
- **API docs:** http://localhost:8000/docs

### 5. Backfill historical data (optional)

```bash
# Stock history (30 days, via Yahoo Finance — free, no API key)
cd ingestion && python backfill_stocks.py

# Crypto history (30 days, via CoinGecko — rate limited, takes ~15 min)
cd ingestion && python backfill_crypto.py
```

## Project Structure

```
MarketPulse/
├── backend/               # FastAPI REST API + ingestion background task
│   ├── main.py            # App entry, lifespan, background loops (ingestion + alerts)
│   ├── config.py          # pydantic-settings config (all env vars)
│   ├── routers/           # prices, stocks, alerts, health endpoints
│   ├── services/          # ingestion, DB queries, cache, alert checker
│   └── models/            # Pydantic request/response models
├── ingestion/             # Standalone ingestion scripts (local/backfill use)
│   ├── fetcher.py         # CoinGecko API client
│   ├── stock_fetcher.py   # Finnhub API client (25 US stocks)
│   ├── backfill_crypto.py # Historical crypto backfill
│   └── backfill_stocks.py # Historical stock backfill (yfinance)
├── frontend/              # React + Vite dashboard
│   ├── src/components/    # PriceCard, StockChart, Watchlist, AlertsPanel, etc.
│   ├── src/hooks/         # React Query hooks
│   ├── src/api/           # Axios API wrappers
│   ├── nginx.conf         # Reverse proxy config
│   └── Dockerfile         # Multi-stage build (Node → nginx)
├── db/migrations/         # SQL schema files
├── docker-compose.yml     # Full local stack
└── .env.example           # Environment variable template
```

## API Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Service health check |
| GET | `/prices/latest` | Latest price for all tracked coins |
| GET | `/prices/{symbol}/history` | Crypto price history (`from`, `to`, `interval`) |
| GET | `/stocks/latest` | Latest price for all tracked stocks |
| GET | `/stocks/{symbol}/history` | Stock price history |
| POST | `/alerts` | Create a price alert |
| GET | `/alerts` | List all alerts |
| DELETE | `/alerts/{id}` | Delete an alert |

## Environment Variables

See [`.env.example`](.env.example) for all variables:

| Variable | Required | Description |
|---|---|---|
| `POSTGRES_*` | Yes | PostgreSQL connection |
| `REDIS_HOST` | Yes | Redis connection |
| `REDIS_SSL` | No | Set `true` for Upstash TLS |
| `FINNHUB_API_KEY` | No | Enables stock data ingestion |
| `FETCH_INTERVAL_SECONDS` | No | Ingestion interval (default: 60) |
| `VITE_API_BASE_URL` | No | API URL baked into frontend at build time |

## Deployment

See [`DEPLOYMENT.md`](DEPLOYMENT.md) for the full production guide covering:
- **Supabase** — managed PostgreSQL
- **Upstash** — serverless Redis with TLS
- **Render** — backend (single Web Service)
- **Vercel** — frontend

## License

MIT
