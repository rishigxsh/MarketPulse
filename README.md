# MarketPulse — Real-Time Stock & Crypto Data Pipeline

> A production-grade financial data platform built end-to-end: ingestion pipeline → Redis message queue → time-series database → REST API → interactive React dashboard.

[![Live Demo](https://img.shields.io/badge/Live%20Demo-Visit%20MarketPulse-brightgreen?logo=vercel&style=for-the-badge)](https://market-pulse-rouge.vercel.app)

![React](https://img.shields.io/badge/React_18-TypeScript-61DAFB?logo=react&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-Python-009688?logo=fastapi&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-4169E1?logo=postgresql&logoColor=white)
![Redis](https://img.shields.io/badge/Redis-Queue%20%2B%20Cache-DC382D?logo=redis&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-yellow)

---

## What This Project Demonstrates

This isn't a tutorial clone — it's a full distributed system designed and built from scratch. Here's what it covers:

- **Distributed pipeline design** — decoupled ingestion, queue, worker, API, and frontend services
- **Async Python** — `asyncio`, `httpx`, `asyncpg` for non-blocking I/O throughout the backend
- **Message queues** — Redis Lists (RPUSH/BLPOP) for reliable producer-consumer data flow
- **Time-series data modeling** — PostgreSQL tables partitioned by timestamp with composite PKs
- **Caching strategy** — Redis cache-aside pattern with 60s TTL to reduce DB load
- **Type safety everywhere** — Pydantic models in Python, TypeScript interfaces in React
- **React best practices** — React Query for server state, no direct fetch in components, custom hooks
- **Production deployment** — live on Vercel + Render + Supabase + Upstash (not just localhost)
- **Docker Compose** — multi-service local dev environment with networking, volumes, and health checks

---

## Live Demo

**[market-pulse-rouge.vercel.app](https://market-pulse-rouge.vercel.app)**

Tracks **50 cryptocurrencies** and **25 US stocks** in real time. Charts update with live data pulled from CoinGecko and Finnhub APIs.

> Note: The backend runs on Render's free tier and may take ~30 seconds to wake up after inactivity.

---

## Architecture

Data flows strictly in one direction — no layer skips another.

```
CoinGecko API (crypto)        Finnhub API (stocks)
        │                              │
        └──────────────┬───────────────┘
                       ▼
         [ Python Ingestion Service ]
           Fetches prices every 60s
                       │
              RPUSH to Redis Lists
                       │
                       ▼
         [ Redis Message Queues ]
      marketpulse:prices:queue
      marketpulse:stocks:queue
                       │
              BLPOP (blocking read)
                       │
                       ▼
         [ Python Worker Service ]
           Validates + writes to DB
                       │
                       ▼
         [ PostgreSQL (Supabase) ]
      crypto_prices + stock_prices
      Indexed by (symbol, timestamp)
                       │
                       ▼
         [ FastAPI REST API ]
       /prices/* + /stocks/* + /alerts/*
       Redis cache-aside (60s TTL)
                       │
                       ▼
         [ React + Vite Dashboard ]
        Recharts, React Query, Tailwind
```

**Why this architecture?**
Separating ingestion from the worker means each can scale independently. If the API source rate-limits us, only the ingestion pod backs off — the worker and API keep serving cached data without interruption.

---

## Features

| Feature | Details |
|---|---|
| Real-time price tracking | 50 cryptos via CoinGecko, 25 US stocks via Finnhub — polled every 60s |
| Interactive charts | 24h, 7d, 30d price history rendered with Recharts |
| Watchlist | Pin favorite assets — persisted to `localStorage` |
| Price alerts | Set above/below thresholds, auto-checked every 30s by the backend |
| Redis caching | 60s TTL cache-aside on all hot endpoints — cuts DB reads by ~90% |
| Historical backfill | Scripts to populate 30 days of OHLC history on first deploy |
| Health endpoint | `/health` for uptime monitoring and container orchestration readiness |
| Fully typed | Pydantic models (Python) + TypeScript interfaces (React) — no `any`, no raw dicts |

---

## Tech Stack

### Backend
- **FastAPI** — async REST API with auto-generated OpenAPI docs
- **asyncpg** — async PostgreSQL driver (no ORM overhead)
- **httpx** — async HTTP client for external API calls
- **Pydantic + pydantic-settings** — data validation and config management
- **Redis** — dual role: message queue (Lists) and response cache (Strings with TTL)

### Frontend
- **React 18** + **TypeScript** — functional components and hooks only
- **React Query (TanStack Query)** — server state, background refetching, loading/error states
- **Recharts** — composable chart library for price history graphs
- **Tailwind CSS** — utility-first styling
- **Vite** — fast dev server and optimized production build
- **Axios** — HTTP client wrapped in `src/api/` (never called directly from components)

### Infrastructure
- **Docker Compose** — six-service local stack (postgres, redis, backend, ingestion, worker, frontend)
- **Supabase** — managed PostgreSQL (free tier, no TimescaleDB — plain tables with indexes)
- **Upstash** — serverless Redis with TLS
- **Render** — backend, ingestion, and worker deployed as Web Services
- **Vercel** — frontend CDN deployment with env var injection at build time

---

## Project Structure

```
MarketPulse/
├── backend/                  # FastAPI REST API
│   ├── main.py               # App entry point, lifespan, alert checker loop
│   ├── config.py             # pydantic-settings — all env vars in one place
│   ├── routers/              # prices.py, stocks.py, alerts.py, health.py
│   ├── services/             # DB queries, Redis cache, alert checker logic
│   └── models/               # Pydantic request/response schemas
│
├── ingestion/                # Data ingestion service (runs independently)
│   ├── main.py               # Fetch loop + Redis RPUSH publisher
│   ├── fetcher.py            # CoinGecko API client
│   ├── stock_fetcher.py      # Finnhub API client
│   ├── backfill_crypto.py    # Historical crypto backfill (30 days)
│   └── backfill_stocks.py    # Historical stock backfill via yfinance
│
├── worker/                   # Queue consumer service
│   └── main.py               # BLPOP from Redis, validate, write to PostgreSQL
│
├── frontend/                 # React + Vite dashboard
│   ├── src/
│   │   ├── api/              # Axios wrappers — all HTTP calls live here
│   │   ├── components/       # PriceCard, StockChart, Watchlist, AlertsPanel
│   │   ├── hooks/            # React Query hooks (usePrices, useStocks, etc.)
│   │   ├── pages/            # Dashboard, Stocks, Crypto pages
│   │   └── types/            # TypeScript interfaces
│   ├── nginx.conf            # SPA routing + reverse proxy config
│   └── Dockerfile            # Multi-stage build: Node (build) → nginx (serve)
│
├── db/migrations/            # Versioned SQL schema files
│   ├── 001_init.sql          # crypto_prices table + indexes
│   └── 002_stock_prices.sql  # stock_prices table + indexes
│
├── docker-compose.yml        # Full local dev stack
└── .env.example              # All required environment variables documented
```

---

## API Reference

All endpoints return a consistent envelope: `{ data, error, timestamp }`.

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Liveness check — returns service status |
| `GET` | `/prices/latest` | Latest price snapshot for all tracked cryptos |
| `GET` | `/prices/{symbol}/history` | Price history with `?from=`, `?to=`, `?interval=` |
| `GET` | `/stocks/latest` | Latest price snapshot for all tracked stocks |
| `GET` | `/stocks/{symbol}/history` | Stock price history |
| `POST` | `/alerts` | Create a price alert (above/below threshold) |
| `GET` | `/alerts` | List all active alerts |
| `DELETE` | `/alerts/{id}` | Remove an alert |

Interactive API docs available at `/docs` (Swagger UI) and `/redoc`.

---

## Running Locally

**Prerequisites:** Docker Desktop installed and running. That's it.

```bash
# 1. Clone the repo
git clone https://github.com/rishigxsh/MarketPulse.git
cd MarketPulse

# 2. Set up environment variables
cp .env.example .env
# Open .env and fill in your API keys (see .env.example for instructions)

# 3. Start all six services
docker compose up --build -d

# 4. Run database migrations (first time only)
docker compose exec postgres psql -U marketpulse -d marketpulse -f /migrations/001_init.sql
docker compose exec postgres psql -U marketpulse -d marketpulse -f /migrations/002_stock_prices.sql
```

**Dashboard:** http://localhost
**API docs:** http://localhost:8000/docs

### Backfill historical data (optional)

```bash
# 30 days of stock history via Yahoo Finance (free, no API key needed)
cd ingestion && python backfill_stocks.py

# 30 days of crypto history via CoinGecko (rate-limited — takes ~15 min)
cd ingestion && python backfill_crypto.py
```

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `POSTGRES_HOST` | Yes | PostgreSQL host |
| `POSTGRES_DB` | Yes | Database name |
| `POSTGRES_USER` | Yes | Database user |
| `POSTGRES_PASSWORD` | Yes | Database password |
| `REDIS_HOST` | Yes | Redis hostname |
| `REDIS_PORT` | Yes | Redis port |
| `REDIS_SSL` | No | Set `true` for Upstash or any TLS Redis |
| `FINNHUB_API_KEY` | No | Enables stock data (free key at finnhub.io) |
| `FETCH_INTERVAL_SECONDS` | No | Ingestion polling interval (default: `60`) |
| `VITE_API_BASE_URL` | No | Backend URL baked into the frontend at build time |

See [`.env.example`](.env.example) for the full template with descriptions.

---

## Key Engineering Decisions

**Why Redis as a message queue instead of Kafka or RabbitMQ?**
Redis Lists with RPUSH/BLPOP give reliable ordered queues with zero infrastructure overhead for this scale. Kafka would be overkill for a pipeline processing ~75 symbols per minute.

**Why separate ingestion and worker services?**
They fail and scale independently. CoinGecko rate-limiting the ingestion pod doesn't affect the worker or API. In production, you could run multiple workers without touching ingestion.

**Why PostgreSQL instead of a dedicated time-series DB?**
Supabase's free tier doesn't support TimescaleDB. The solution uses a composite `(symbol, timestamp)` primary key with a `timestamp` index — enough to serve sub-100ms historical queries at this data volume.

**Why React Query instead of Redux or Zustand?**
Server data (prices, alerts) has different lifecycle requirements than UI state. React Query handles caching, background refetching, and loading/error states declaratively — no boilerplate reducers needed.

---

## Production Deployment

Full guide in [`DEPLOYMENT.md`](DEPLOYMENT.md), covering:
- Supabase PostgreSQL setup and migrations
- Upstash Redis with TLS configuration
- Render Web Services for backend, ingestion, and worker
- Vercel frontend deploy with environment variable injection

**Live infrastructure:**

| Service | Provider | Notes |
|---|---|---|
| Frontend | Vercel | Auto-deploys on push to `main` |
| Backend API | Render | Free tier — cold starts after inactivity |
| Ingestion | Render | Runs health server on port 10000 (Render requirement) |
| Worker | Render | Same pattern — BLPOP keeps process alive |
| Database | Supabase | Session Pooler on port 5432 for IPv4 compatibility |
| Redis | Upstash | Serverless Redis with TLS (`REDIS_SSL=true`) |

---

## License

MIT — free to use, fork, and build on.
