# MarketPulse — Real-Time Stock & Crypto Data Pipeline

A full-stack financial data pipeline that ingests real-time cryptocurrency and stock market data, stores it in a time-series database, and visualizes it through an interactive dashboard.

![React](https://img.shields.io/badge/React-18-blue?logo=react)
![FastAPI](https://img.shields.io/badge/FastAPI-0.110-green?logo=fastapi)
![TimescaleDB](https://img.shields.io/badge/TimescaleDB-PostgreSQL_15-blue?logo=postgresql)
![Docker](https://img.shields.io/badge/Docker-Compose-blue?logo=docker)
![License](https://img.shields.io/badge/License-MIT-yellow)

## Architecture

```
CoinGecko API (crypto)     Finnhub API (stocks)
        │                          │
        ▼                          ▼
   [ Python Ingestion — dual fetcher ]
        │
        ▼
   [ Redis Queues ]
        │
        ▼
   [ TimescaleDB ]
        │
        ▼
   [ FastAPI Backend ]
        │
        ▼
   [ React + Vite Dashboard ]
```

Data flows strictly in one direction: **Ingestion → Queue → Storage → API → UI**

## Features

- **Real-time price tracking** — 50 cryptocurrencies (CoinGecko) + 25 US stocks (Finnhub)
- **Interactive charts** — 24h, 7d, and 30d price history with Recharts
- **Crypto/Stocks tabs** — separate views with distinct color themes (indigo/emerald)
- **Watchlist** — pin favorite coins with localStorage persistence
- **Price alerts** — set above/below triggers, auto-checked every 30s
- **Time-series storage** — TimescaleDB hypertables with hourly/daily bucketing
- **Redis caching** — 60s TTL on API responses for fast reads
- **Historical backfill** — scripts to populate 30 days of historical data
- **Docker Compose** — full 6-service stack runs with one command

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 18, TypeScript, Vite, Tailwind CSS, Recharts, React Query |
| Backend | FastAPI, asyncpg, Redis, Pydantic |
| Database | TimescaleDB (PostgreSQL 15) |
| Queue | Redis (List — RPUSH/BLPOP) |
| Ingestion | Python, httpx, CoinGecko API, Finnhub API |
| Deployment | Docker Compose, nginx reverse proxy |

## Quick Start

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running
- A free [CoinGecko API](https://www.coingecko.com/en/api) key (optional — works without it)
- A free [Finnhub API](https://finnhub.io/) key (optional — stocks disabled without it)

### 1. Clone and configure

```bash
git clone https://github.com/rishigxsh/MarketPulse.git
cd MarketPulse
cp .env.example .env
# Edit .env — fill in your API keys and DB credentials
```

### 2. Start infrastructure

```bash
docker compose up -d postgres redis
```

Wait ~10 seconds, then run migrations:

```bash
docker compose exec postgres psql -U marketpulse -d marketpulse \
  -c "CREATE EXTENSION IF NOT EXISTS timescaledb;"
docker compose exec postgres psql -U marketpulse -d marketpulse \
  -f /migrations/001_init.sql
docker compose exec postgres psql -U marketpulse -d marketpulse \
  -f /migrations/002_stock_prices.sql
```

### 3. Start all services

```bash
docker compose up -d
```

### 4. Open the dashboard

- **Dashboard:** http://localhost (nginx, port 80)
- **API docs:** http://localhost:8000/docs
- **Dev server:** `cd frontend && npm install && npm run dev` → http://localhost:5173

### 5. Backfill historical data (optional)

```bash
# Stock history (30 days, via Yahoo Finance — free, no API key)
docker compose exec -e POSTGRES_HOST=postgres ingestion python backfill_stocks.py

# Crypto history (30 days, via CoinGecko — rate limited, takes ~15 min)
docker compose exec -e POSTGRES_HOST=postgres ingestion python backfill_crypto.py
```

## Project Structure

```
MarketPulse/
├── backend/               # FastAPI REST API
│   ├── main.py            # App entry, lifespan, CORS, routers
│   ├── routers/           # prices, stocks, alerts, health endpoints
│   ├── services/          # DB queries, cache, alert checker
│   └── models/            # Pydantic response models
├── ingestion/             # Data ingestion scripts
│   ├── main.py            # Async scheduler loop
│   ├── fetcher.py         # CoinGecko API client
│   ├── stock_fetcher.py   # Finnhub API client (25 US stocks)
│   ├── publisher.py       # Redis queue publisher
│   ├── backfill_crypto.py # Historical crypto backfill
│   └── backfill_stocks.py # Historical stock backfill (yfinance)
├── worker/                # Queue consumer
│   ├── main.py            # BLPOP loop for both queues
│   └── db.py              # TimescaleDB writer
├── frontend/              # React + Vite dashboard
│   ├── src/components/    # PriceCard, PriceChart, Watchlist, AlertsPanel, etc.
│   ├── src/hooks/         # React Query hooks
│   ├── src/api/           # Axios API wrappers
│   ├── nginx.conf         # Reverse proxy config
│   └── Dockerfile         # Multi-stage build (Node → nginx)
├── db/migrations/         # TimescaleDB schema
├── docker-compose.yml     # Full 6-service stack
└── docker-compose.prod.yml # Production overrides
```

## API Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Service health check |
| GET | `/prices/latest` | Latest price for all tracked coins |
| GET | `/prices/{symbol}/history` | Crypto price history (params: `from`, `to`, `interval`) |
| GET | `/stocks/latest` | Latest price for all tracked stocks |
| GET | `/stocks/{symbol}/history` | Stock price history |
| POST | `/alerts` | Create a price alert |
| GET | `/alerts` | List all alerts |
| DELETE | `/alerts/{id}` | Delete an alert |

## Environment Variables

See [`.env.example`](.env.example) for all required variables:

| Variable | Required | Description |
|---|---|---|
| `POSTGRES_*` | Yes | TimescaleDB connection |
| `REDIS_HOST` | Yes | Redis connection |
| `FINNHUB_API_KEY` | No | Enables stock data ingestion |
| `VITE_API_BASE_URL` | No | API URL for frontend (empty = relative/proxy) |

## Deployment

See [`DEPLOYMENT.md`](DEPLOYMENT.md) for a full production deployment guide using:
- **Supabase** — PostgreSQL + TimescaleDB
- **Upstash** — Serverless Redis
- **Render** — Backend, ingestion, worker (Docker)
- **Vercel** — Frontend (static)

## License

MIT
