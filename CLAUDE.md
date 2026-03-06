# CLAUDE.md — MarketPulse: Real-Time Stock & Crypto Data Pipeline

This file is the authoritative guide for Claude Code when working in this project.
Read it fully before writing or modifying any code.

---

## 1. Project Overview & Architecture Summary

**MarketPulse** is a real-time financial data pipeline that ingests cryptocurrency market data,
stores it in a time-series database, exposes it via a REST API, and visualizes it in a React dashboard.

### High-Level Architecture

```
CoinGecko API (external)
        │
        ▼
[ Python Ingestion Script ]
        │  pushes JSON messages
        ▼
[ Redis Queue (List / Stream) ]
        │  worker pops messages
        ▼
[ TimescaleDB (PostgreSQL) ]
        │  queried by
        ▼
[ FastAPI Backend ]
        │  consumed by
        ▼
[ React + Vite Frontend ]
```

Data flows strictly in one direction: ingestion → storage → API → UI.
No layer skips another. No layer calls backwards.

---

## 2. Folder Structure Conventions

```
marketpulse/
├── CLAUDE.md                   ← this file
├── docker-compose.yml          ← local dev orchestration
├── .env.example                ← template for all env vars (no real values)
├── .env                        ← real env vars (git-ignored)
│
├── ingestion/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py                 ← entry point, scheduler loop
│   ├── fetcher.py              ← CoinGecko API calls
│   ├── publisher.py            ← pushes to Redis queue
│   └── models.py               ← Pydantic models for raw API responses
│
├── worker/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py                 ← entry point, Redis consumer loop
│   ├── db.py                   ← TimescaleDB write logic
│   └── models.py               ← Pydantic models for DB records
│
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py                 ← FastAPI app entrypoint
│   ├── routers/
│   │   ├── prices.py
│   │   └── health.py
│   ├── services/
│   │   ├── cache.py            ← Redis cache reads/writes
│   │   └── db.py               ← TimescaleDB query logic
│   ├── models/
│   │   ├── responses.py        ← Pydantic response models
│   │   └── db.py               ← Pydantic DB row models
│   └── config.py               ← settings loaded from env via pydantic-settings
│
├── frontend/
│   ├── index.html
│   ├── vite.config.ts
│   ├── tailwind.config.ts
│   ├── src/
│   │   ├── main.tsx
│   │   ├── App.tsx
│   │   ├── components/         ← reusable UI components
│   │   ├── pages/              ← route-level page components
│   │   ├── hooks/              ← custom React Query hooks
│   │   ├── api/                ← axios/fetch wrappers for backend calls
│   │   └── types/              ← TypeScript interfaces matching API responses
│   └── package.json
│
└── db/
    └── migrations/
        └── 001_init.sql        ← schema + hypertable creation
```

One service per folder. Never mix concerns across folders.

---

## 3. Coding Standards

### Python (ingestion, worker, backend)

- **Type hints are mandatory** on every function signature — arguments and return types.
- **Pydantic models everywhere.** Never pass raw `dict` objects between functions or across
  service boundaries. Define a model, validate into it, pass the model.
- Use `pydantic-settings` (`BaseSettings`) in `config.py` to load all configuration from
  environment variables. Never call `os.environ.get()` directly in business logic.
- Use `async`/`await` throughout FastAPI. Blocking calls belong in a thread pool via
  `asyncio.to_thread()` if unavoidable.
- Format all Python code with **Black** (line length 88). Lint with **Ruff**.
- Log using Python's `logging` module (structured where possible). Never use `print()` in
  production code paths.

### TypeScript / React (frontend)

- **Functional components only.** No class components, ever.
- Every component file exports a single default component. Name matches filename.
- All server state is managed via **React Query** (`useQuery`, `useMutation`). No manual
  `useEffect` + `fetch` patterns for server data.
- All API call wrappers live in `src/api/`. Components never call `fetch` or `axios` directly.
- Props interfaces are defined inline above the component or in `src/types/`.
- Use Tailwind utility classes for all styling. No inline `style={{}}` objects except for
  dynamic values that can't be expressed in Tailwind.
- Charts are built with **Recharts** only. No mixing charting libraries.

---

## 4. Environment Variables

All environment variables are declared in `.env.example` with placeholder values.
The real `.env` file is **git-ignored and never committed**.

**Never hardcode any credential, key, URL, or port in source code.**
Every configurable value must come from an environment variable.

### Required Variables

```env
# PostgreSQL / TimescaleDB
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=marketpulse
POSTGRES_USER=your_db_user
POSTGRES_PASSWORD=your_db_password

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=                     # leave blank if no auth locally

# CoinGecko
COINGECKO_API_KEY=your_api_key_here  # required for Pro; omit for free-tier demo mode

# FastAPI
API_HOST=0.0.0.0
API_PORT=8000
CORS_ORIGINS=http://localhost:5173

# Frontend (Vite exposes vars prefixed with VITE_)
VITE_API_BASE_URL=http://localhost:8000
```

Load in Python via:
```python
# backend/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    postgres_host: str
    postgres_port: int = 5432
    postgres_db: str
    postgres_user: str
    postgres_password: str
    redis_host: str
    redis_port: int = 6379
    coingecko_api_key: str = ""

    class Config:
        env_file = ".env"

settings = Settings()
```

---

## 5. How Each Layer Connects

### Ingestion → Redis Queue

`ingestion/fetcher.py` calls the CoinGecko `/coins/markets` endpoint on a schedule
(default: every 60 seconds). The response is validated into a Pydantic model and
serialized to JSON. `ingestion/publisher.py` pushes each record onto a Redis List
(key: `marketpulse:prices:queue`) using `RPUSH`.

### Redis Queue → TimescaleDB

`worker/main.py` runs a blocking loop (`BLPOP`) consuming from the same Redis List.
Each message is deserialized, validated into a Pydantic model, and written to TimescaleDB
via `worker/db.py`. The worker is a separate process/container from the ingestion script.

### TimescaleDB → FastAPI

`backend/services/db.py` uses `asyncpg` (or `databases`) to query TimescaleDB.
All query results are mapped to Pydantic models before being returned to routers.
`backend/services/cache.py` wraps frequently-hit queries with Redis caching
(TTL: 30 seconds by default). Cache-aside pattern: check Redis → on miss, query DB → write to Redis.

### FastAPI → React

The React frontend calls FastAPI endpoints exclusively through wrappers in `src/api/`.
React Query manages caching, background refetch, and loading/error states.
All data is typed via TypeScript interfaces in `src/types/` that mirror the backend
Pydantic response models.

---

## 6. Database Conventions

- **All price data tables must be TimescaleDB hypertables.** Create them via
  `SELECT create_hypertable('table_name', 'timestamp');` immediately after `CREATE TABLE`.
- **Every table that stores time-series data must have a `timestamp TIMESTAMPTZ NOT NULL` column.**
  This is the hypertable partition key.
- Use `TIMESTAMPTZ` (not `TIMESTAMP`) for all time columns — always store in UTC.
- Table names: lowercase, snake_case, plural (e.g., `crypto_prices`, `market_snapshots`).
- Never use `SERIAL` primary keys on hypertables. Use a composite primary key of
  `(symbol, timestamp)` or omit a surrogate key entirely.
- All schema changes go in numbered migration files under `db/migrations/`.
  Never alter the schema by hand in a running database.

### Example Schema

```sql
-- db/migrations/001_init.sql

CREATE TABLE IF NOT EXISTS crypto_prices (
    symbol        TEXT         NOT NULL,
    name          TEXT         NOT NULL,
    price_usd     NUMERIC(20, 8) NOT NULL,
    market_cap    BIGINT,
    volume_24h    BIGINT,
    price_change_24h NUMERIC(10, 4),
    timestamp     TIMESTAMPTZ  NOT NULL
);

SELECT create_hypertable('crypto_prices', 'timestamp');

CREATE INDEX ON crypto_prices (symbol, timestamp DESC);
```

---

## 7. API Conventions

Every endpoint in FastAPI **must** return a consistent JSON envelope:

```json
{
  "data": <payload or null>,
  "error": <error message string or null>,
  "timestamp": "<ISO 8601 UTC string>"
}
```

Define this as a generic Pydantic response model:

```python
# backend/models/responses.py
from typing import Generic, Optional, TypeVar
from pydantic import BaseModel
from datetime import datetime, timezone

T = TypeVar("T")

class APIResponse(BaseModel, Generic[T]):
    data: Optional[T] = None
    error: Optional[str] = None
    timestamp: str = datetime.now(timezone.utc).isoformat()
```

All routers return `APIResponse[SomeModel]`. On success: `data` is populated, `error` is null.
On failure: `data` is null, `error` is a human-readable message.

HTTP status codes still apply normally (`200`, `404`, `422`, `500`).

---

## 8. Error Handling Rules

- **Every external API call (CoinGecko, any third-party HTTP request) must be wrapped in
  `try/except`.** Log the error. Re-raise or return a structured error — never swallow it silently.
- **Every database write and read must be wrapped in `try/except`.** Log with context
  (which record failed, what the query was).
- Use Python's `logging` module at the appropriate level:
  - `logging.error(...)` for failures that break flow
  - `logging.warning(...)` for recoverable issues
  - `logging.info(...)` for normal operational events
  - `logging.debug(...)` for verbose diagnostics
- In FastAPI, use an exception handler or HTTPException for known error cases.
  Unhandled exceptions should be caught by a global middleware that returns a 500
  in the standard `APIResponse` envelope.
- The ingestion script must **not crash on a single bad fetch**. It must log, skip
  the failed cycle, and resume on the next interval.

### Example Pattern

```python
# ingestion/fetcher.py
import logging
import httpx
from models import CoinGeckoResponse

logger = logging.getLogger(__name__)

async def fetch_prices(api_key: str) -> list[CoinGeckoResponse]:
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {"vs_currency": "usd", "order": "market_cap_desc", "per_page": 50}
    try:
        async with httpx.AsyncClient() as client:
            response = client.get(url, params=params, timeout=10)
            response.raise_for_status()
            return [CoinGeckoResponse(**item) for item in response.json()]
    except httpx.HTTPStatusError as e:
        logger.error("CoinGecko API returned %s: %s", e.response.status_code, e)
        return []
    except Exception as e:
        logger.error("Unexpected error fetching prices: %s", e)
        return []
```

---

## 9. How to Run the Project Locally

### Prerequisites

- Docker Desktop installed and running
- Node.js 18+ and npm/pnpm installed (for frontend)
- Python 3.11+ (optional if running everything via Docker)

### Step 1 — Clone and configure environment

```bash
git clone <repo-url>
cd marketpulse
cp .env.example .env
# Edit .env and fill in all required values
```

### Step 2 — Start infrastructure (DB + Redis)

```bash
docker compose up -d postgres redis
```

Wait ~10 seconds for TimescaleDB to initialize, then run migrations:

```bash
docker compose exec postgres psql -U $POSTGRES_USER -d $POSTGRES_DB -f /migrations/001_init.sql
```

> [MANUAL STEP REQUIRED]
> TimescaleDB must be enabled as a PostgreSQL extension before running migrations.
> Connect to your PostgreSQL instance and run:
> ```sql
> CREATE EXTENSION IF NOT EXISTS timescaledb;
> ```
> The `docker-compose.yml` should use the `timescale/timescaledb:latest-pg15` image,
> which ships with the extension pre-installed. If using an external managed PostgreSQL
> (e.g., Railway, Supabase), you must enable the extension manually in their dashboard
> or via a migration — TimescaleDB is not available on all providers.
> Railway does NOT support TimescaleDB. Use Supabase or a raw Docker deployment instead.

### Step 3 — Start ingestion and worker

```bash
docker compose up -d ingestion worker
```

Verify data is flowing:
```bash
docker compose logs -f ingestion
docker compose logs -f worker
```

### Step 4 — Start the backend API

```bash
docker compose up -d backend
# API is now available at http://localhost:8000
# Docs at http://localhost:8000/docs
```

### Step 5 — Start the frontend

```bash
cd frontend
npm install
npm run dev
# App is now available at http://localhost:5173
```

### Step 6 — Verify end-to-end

Open `http://localhost:5173` — you should see live crypto price charts populating
within 60–90 seconds of ingestion starting.

---

## 10. What NOT To Do

These are hard rules. Do not violate them.

| Rule | Why |
|---|---|
| **No direct DB calls from the frontend.** | The database is never exposed to the browser. All data goes through FastAPI. |
| **No API keys or credentials in source code.** | They will end up in git history. Use `.env` + `.env.example`. |
| **No skipping Pydantic validation.** | Raw dicts passed between services are the #1 source of silent data bugs. |
| **No raw SQL strings built via f-strings or string concatenation.** | SQL injection. Use parameterized queries exclusively. |
| **No class components in React.** | Project standard is functional components + hooks. |
| **No direct `fetch`/`axios` calls inside React components.** | All API calls go through `src/api/` wrappers, consumed via React Query hooks. |
| **No storing passwords or secrets in Docker image layers.** | Pass secrets via environment variables at runtime, not build time. |
| **No altering TimescaleDB schema without a migration file.** | Every schema change must be reproducible and versioned. |
| **No silent `except: pass` blocks.** | Every caught exception must be logged. |
| **No mixing ingestion and worker logic in the same process.** | They scale independently. Keep them separate containers. |

---

## Manual Steps Summary

The following require action outside of this codebase:

1. **[MANUAL STEP REQUIRED] CoinGecko API Key**
   - Free tier: Go to https://www.coingecko.com/en/api and register for a free Demo API key.
   - The free tier supports up to 10,000 calls/month and doesn't require a credit card.
   - Set `COINGECKO_API_KEY` in your `.env` file.
   - Rate limit: ~30 calls/minute on free tier. The ingestion interval must be >= 60 seconds.

2. **[MANUAL STEP REQUIRED] TimescaleDB Extension**
   - If using the provided Docker Compose setup with `timescale/timescaledb` image, the
     extension is pre-installed. Run `CREATE EXTENSION IF NOT EXISTS timescaledb;` once.
   - If deploying to a managed PostgreSQL provider, verify TimescaleDB is supported.
     Supabase supports it. Railway does NOT. Render does NOT natively.

3. **[MANUAL STEP REQUIRED] Production Deployment (Render)**
   - Create a Render account at https://render.com
   - Create a PostgreSQL instance — note: native TimescaleDB is not available on Render's
     managed PG. You must use a Docker-based Web Service with the TimescaleDB image instead.
   - Alternatively, use Supabase for the database (supports TimescaleDB) + Render for the
     FastAPI backend + a static site host (Netlify/Vercel) for the frontend.
   - Set all environment variables in the Render dashboard under Environment → Secret Files.

4. **[MANUAL STEP REQUIRED] Redis on Production**
   - Use Upstash (https://upstash.com) for a free-tier serverless Redis instance compatible
     with Railway and Render.
   - Copy the Upstash Redis URL into `REDIS_HOST`, `REDIS_PORT`, and `REDIS_PASSWORD` in
     your production environment config.

---

*Last updated: 2026-03-06*
*Project: MarketPulse — Real-Time Stock & Crypto Data Pipeline*

---

## 11. Build Plan

This section defines the full 8-phase build order. Each phase is a shippable increment.
Do not start the next phase until the verify step passes.

### Architecture Decisions (locked)

| # | Decision | Choice | Reason |
|---|---|---|---|
| D1 | Fetch interval | 60s | Free CoinGecko tier ~10,000 calls/month; 30s = 43,200 = over limit |
| D2 | Redis transport | List (RPUSH/BLPOP) | Simpler than Streams; sufficient for single-worker local dev |
| D3 | Python DB driver | asyncpg directly | Faster for time-series bulk writes; cleaner TimescaleDB queries |
| D4 | Alert persistence | PostgreSQL table (`price_alerts`) | Survives container restarts; in-memory lost on restart |
| D5 | Frontend routing | Single-page layout | No React Router; dashboard, watchlist, alerts are panels on one page |

---

### Phase 1 — Project Setup

**Goal:** Scaffold folder structure, Docker Compose, env config, and a minimal FastAPI that boots.

| File | Purpose |
|---|---|
| `docker-compose.yml` | Orchestrates postgres (TimescaleDB), redis, backend; ingestion + worker use `profiles: [pipeline]` |
| `.env.example` | All env var templates, no real values |
| `.gitignore` | Ignores `.env`, `__pycache__`, `node_modules`, `.venv`, `*.pyc` |
| `backend/main.py` | FastAPI app: creates app instance, registers routers, CORS middleware, global exception handler |
| `backend/config.py` | `pydantic-settings` BaseSettings loading all env vars |
| `backend/requirements.txt` | fastapi, uvicorn, asyncpg, redis, pydantic-settings, httpx |
| `backend/Dockerfile` | Python 3.11 slim, installs requirements, runs uvicorn |
| `backend/models/__init__.py` | Empty init |
| `backend/models/responses.py` | Generic `APIResponse[T]` Pydantic model |
| `backend/routers/__init__.py` | Empty init |
| `backend/routers/health.py` | `GET /health` returns `{status: ok, timestamp}` |
| `backend/services/__init__.py` | Empty init |
| `ingestion/__init__.py` | Empty |
| `worker/__init__.py` | Empty |
| `db/migrations/001_init.sql` | Placeholder — full schema written in Phase 2 |

Docker Compose services: `postgres` (timescale/timescaledb:latest-pg15, port 5432, mounts `db/migrations/` to `/migrations`), `redis` (redis:7-alpine, port 6379), `backend` (depends_on postgres + redis, port 8000). Ingestion + worker defined under `profiles: [pipeline]` — not started until Phase 3/4.

> [MANUAL STEP REQUIRED] Install Docker Desktop if not already running.
> [MANUAL STEP REQUIRED] Copy `.env.example` to `.env` and fill in POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB=marketpulse.

**Verify:**
```bash
docker compose up -d postgres redis backend
curl http://localhost:8000/health
# Expected: {"data":{"status":"ok"},"error":null,"timestamp":"..."}
docker compose logs backend  # No errors
```

---

### Phase 2 — Database Layer

**Goal:** Write the full TimescaleDB schema, run migrations, confirm hypertables are active.

| File | Purpose |
|---|---|
| `db/migrations/001_init.sql` | Full schema: `crypto_prices` hypertable + `price_alerts` table + indexes |

`crypto_prices` hypertable (partitioned by `timestamp`): `symbol TEXT`, `name TEXT`, `price_usd NUMERIC(20,8)`, `market_cap BIGINT`, `volume_24h BIGINT`, `price_change_24h NUMERIC(10,4)`, `timestamp TIMESTAMPTZ NOT NULL`. Composite index on `(symbol, timestamp DESC)`.

`price_alerts` regular table: `id SERIAL PRIMARY KEY`, `symbol TEXT`, `target_price NUMERIC(20,8)`, `direction TEXT` ('above'/'below'), `triggered BOOLEAN DEFAULT FALSE`, `created_at TIMESTAMPTZ DEFAULT NOW()`, `triggered_at TIMESTAMPTZ`.

> [MANUAL STEP REQUIRED] After `docker compose up -d postgres`, run:
> ```bash
> docker compose exec postgres psql -U $POSTGRES_USER -d $POSTGRES_DB \
>   -c "CREATE EXTENSION IF NOT EXISTS timescaledb;"
> docker compose exec postgres psql -U $POSTGRES_USER -d $POSTGRES_DB \
>   -f /migrations/001_init.sql
> ```

**Verify:**
```bash
docker compose exec postgres psql -U $POSTGRES_USER -d $POSTGRES_DB \
  -c "SELECT hypertable_name FROM timescaledb_information.hypertables;"
# Must return: crypto_prices
docker compose exec postgres psql -U $POSTGRES_USER -d $POSTGRES_DB -c "\dt"
# Must show: crypto_prices, price_alerts
```

---

### Phase 3 — Ingestion Layer

**Goal:** Python script fetches top 50 coins from CoinGecko every 60s and pushes each as JSON to the Redis queue.

| File | Purpose |
|---|---|
| `ingestion/requirements.txt` | httpx, redis, pydantic, pydantic-settings |
| `ingestion/Dockerfile` | Python 3.11 slim, installs requirements, runs `python main.py` |
| `ingestion/config.py` | BaseSettings: REDIS_HOST, REDIS_PORT, REDIS_PASSWORD, COINGECKO_API_KEY, FETCH_INTERVAL_SECONDS=60 |
| `ingestion/models.py` | Pydantic model `CoinGeckoPrice` matching CoinGecko `/coins/markets` response fields |
| `ingestion/fetcher.py` | `async fetch_prices() -> list[CoinGeckoPrice]` — calls CoinGecko, validates, returns list. Full try/except with logging. |
| `ingestion/publisher.py` | `publish_prices(prices) -> int` — serializes each to JSON, RPUSHes to `marketpulse:prices:queue`. Returns count pushed. |
| `ingestion/main.py` | Async scheduler loop: fetch → publish every FETCH_INTERVAL_SECONDS. Catches/logs errors per cycle without crashing. |

CoinGecko endpoint: `GET https://api.coingecko.com/api/v3/coins/markets` with params `vs_currency=usd`, `order=market_cap_desc`, `per_page=50`, `page=1` and header `x-cg-demo-api-key: {COINGECKO_API_KEY}`.

> [MANUAL STEP REQUIRED] Register for a free CoinGecko Demo API key at coingecko.com/api. Set `COINGECKO_API_KEY` in `.env`.

**Verify:**
```bash
docker compose --profile pipeline up -d ingestion
docker compose logs -f ingestion
# Must show: "Fetched 50 coins", "Published 50 messages to queue"
docker compose exec redis redis-cli LLEN marketpulse:prices:queue  # Must return > 0
docker compose exec redis redis-cli LRANGE marketpulse:prices:queue 0 0  # Valid JSON
```

---

### Phase 4 — Queue Consumer (Worker)

**Goal:** Worker continuously reads from the Redis queue and writes validated price records into TimescaleDB.

| File | Purpose |
|---|---|
| `worker/requirements.txt` | redis, asyncpg, pydantic, pydantic-settings |
| `worker/Dockerfile` | Python 3.11 slim, installs requirements, runs `python main.py` |
| `worker/config.py` | BaseSettings: REDIS_HOST/PORT/PASSWORD, POSTGRES_* vars |
| `worker/models.py` | Pydantic model `PriceRecord` — mirrors `crypto_prices` columns; uses CoinGecko's `last_updated` as `timestamp` |
| `worker/db.py` | `async write_price(pool, record) -> None` — parameterized INSERT into `crypto_prices`. try/except with logging. |
| `worker/main.py` | Async loop: BLPOP from Redis (timeout=5s), deserialize → validate → write to DB. Creates asyncpg pool on startup. |

**Verify:**
```bash
docker compose --profile pipeline up -d worker
docker compose logs -f worker  # Must show: "Wrote price record: BTC" etc.
docker compose exec postgres psql -U $POSTGRES_USER -d $POSTGRES_DB \
  -c "SELECT symbol, price_usd, timestamp FROM crypto_prices ORDER BY timestamp DESC LIMIT 5;"
# Must return rows with real prices
```

---

### Phase 5 — FastAPI Backend

**Goal:** REST API exposing price data with Redis caching. All responses use `APIResponse[T]` envelope.

| File | Purpose |
|---|---|
| `backend/services/db.py` | asyncpg query functions: `get_latest_prices()`, `get_price_history()`, `create_alert()`, `get_alerts()` |
| `backend/services/cache.py` | `get_cached(key)`, `set_cached(key, value, ttl=60)` — Redis JSON cache helpers |
| `backend/models/db.py` | Pydantic models for DB rows: `CryptoPrice`, `PriceAlert` |
| `backend/routers/prices.py` | All price + alert endpoints |
| `backend/main.py` | Register prices router; startup event creates asyncpg pool + redis connection |

| Method | Path | Cache TTL | Description |
|---|---|---|---|
| GET | `/health` | none | Service liveness check |
| GET | `/prices/latest` | 60s | Latest price for all tracked coins |
| GET | `/prices/{symbol}/history` | 60s | Price history — params: `from`, `to` (ISO), `interval` (optional: `1h`, `1d`) |
| POST | `/alerts` | none | Create alert — body: `{symbol, target_price, direction}` |
| GET | `/alerts` | none | List all alerts |
| DELETE | `/alerts/{id}` | none | Delete an alert |

Cache keys: `cache:latest`, `cache:history:{symbol}:{from}:{to}`. TTL: 60s.

**Verify:**
```bash
curl http://localhost:8000/prices/latest
# Returns {data: [...50 coins...], error: null, timestamp: "..."}
curl "http://localhost:8000/prices/bitcoin/history?from=2026-03-05T00:00:00Z&to=2026-03-06T00:00:00Z"
curl -X POST http://localhost:8000/alerts \
  -H "Content-Type: application/json" \
  -d '{"symbol":"bitcoin","target_price":100000,"direction":"above"}'
# Verify http://localhost:8000/docs loads Swagger UI
```

---

### Phase 6 — Price Alert System

**Goal:** FastAPI background task polls `crypto_prices` every 30s, checks untriggered alerts, marks triggered ones.

| File | Purpose |
|---|---|
| `backend/services/alerts.py` | `check_alerts(pool, redis) -> list[TriggeredAlert]` — queries latest price per symbol, compares against active alerts, updates `triggered=true` + `triggered_at` for hits |
| `backend/routers/prices.py` | Add `GET /alerts/triggered` endpoint |
| `backend/main.py` | Add `asyncio.create_task(alert_loop())` in startup event — runs `check_alerts()` every 30s |

Alert logic: for each untriggered alert, if `direction == 'above' and latest_price >= target_price` → trigger; if `direction == 'below' and latest_price <= target_price` → trigger. No push notifications — alerts flagged in DB, surfaced via API.

**Verify:**
```bash
curl -X POST http://localhost:8000/alerts \
  -d '{"symbol":"bitcoin","target_price":1,"direction":"above"}'
# Wait 35 seconds
curl http://localhost:8000/alerts  # triggered field should be true
docker compose logs backend | grep "Alert triggered"
```

---

### Phase 7 — React Frontend

**Goal:** React + Vite dashboard with live price cards, historical chart, watchlist, and alerts panel.

> [MANUAL STEP REQUIRED] Run from `frontend/` directory before Claude writes frontend files:
> ```bash
> npm create vite@latest . -- --template react-ts
> npm install @tanstack/react-query recharts axios tailwindcss @tailwindcss/vite
> npx tailwindcss init
> ```

| File | Purpose |
|---|---|
| `frontend/vite.config.ts` | Vite config with `@tailwindcss/vite` plugin and proxy `/api → http://localhost:8000` |
| `frontend/tailwind.config.ts` | Tailwind content paths |
| `frontend/src/main.tsx` | App entry: wraps `<App>` in `QueryClientProvider` |
| `frontend/src/App.tsx` | Root layout: header + 3-column grid (PriceCards, Chart, Watchlist+Alerts) |
| `frontend/src/types/index.ts` | TypeScript interfaces: `APIResponse<T>`, `CryptoPrice`, `PriceAlert`, `PriceHistory` |
| `frontend/src/api/prices.ts` | `fetchLatestPrices()`, `fetchPriceHistory(symbol, from, to)` — axios wrappers |
| `frontend/src/api/alerts.ts` | `fetchAlerts()`, `createAlert(payload)`, `deleteAlert(id)` — axios wrappers |
| `frontend/src/hooks/usePrices.ts` | `useLatestPrices()` — useQuery, refetchInterval: 30000 |
| `frontend/src/hooks/usePriceHistory.ts` | `usePriceHistory(symbol, from, to)` — useQuery |
| `frontend/src/hooks/useAlerts.ts` | `useAlerts()`, `useCreateAlert()`, `useDeleteAlert()` |
| `frontend/src/components/PriceCard.tsx` | Single coin card: symbol, price, 24h change (green/red), market cap |
| `frontend/src/components/PriceGrid.tsx` | Grid of PriceCards with skeleton loaders while loading |
| `frontend/src/components/PriceChart.tsx` | Recharts LineChart for selected coin. Responsive container, custom tooltip. |
| `frontend/src/components/Watchlist.tsx` | Pinned coins stored in localStorage. Click to load chart. |
| `frontend/src/components/AlertsPanel.tsx` | Lists alerts, highlights triggered ones in amber. Form to create new alert. |
| `frontend/src/components/SkeletonCard.tsx` | Tailwind pulse skeleton for loading states |
| `frontend/src/pages/Dashboard.tsx` | Assembles all components into the main dashboard page |

UX: dark theme (`bg-gray-950`), default chart coin `bitcoin`, chart default range last 24h (dropdown for 7d/30d), triggered alerts show amber border + "TRIGGERED" badge, price change green/red text.

**Verify:**
```bash
cd frontend && npm run dev
# Open http://localhost:5173
# Price cards visible and updating every 30s
# Clicking a coin loads its chart
# Alert creation form works
# No console errors
```

---

### Phase 8 — Deployment

**Goal:** Finalize Docker Compose for full local stack and write production deployment instructions.

| File | Purpose |
|---|---|
| `docker-compose.yml` | Remove `profiles` flag — all 5 services run by default |
| `docker-compose.prod.yml` | Production overrides: no volume mounts, `restart: always`, pulls from registry |
| `frontend/Dockerfile` | Multi-stage: Node build → nginx:alpine serve |
| `backend/.dockerignore` | Exclude `.env`, `__pycache__`, `.venv` |
| `ingestion/.dockerignore` | Same |
| `worker/.dockerignore` | Same |
| `DEPLOYMENT.md` | Step-by-step Render/Supabase/Upstash/Vercel deployment guide |

Production stack: **Database** → Supabase (supports TimescaleDB; Railway does NOT). **Backend/ingestion/worker** → Render (Docker deploy). **Redis** → Upstash (free serverless). **Frontend** → Vercel (static from `frontend/dist`).

> [MANUAL STEP REQUIRED] Create Supabase project, enable TimescaleDB extension, run `001_init.sql`.
> [MANUAL STEP REQUIRED] Create Upstash Redis instance, copy connection URL to prod env vars.
> [MANUAL STEP REQUIRED] Create Render services for backend, ingestion, worker — set all env vars in dashboard.
> [MANUAL STEP REQUIRED] Deploy frontend to Vercel — set `VITE_API_BASE_URL` to Render backend URL.

**Verify (full local stack):**
```bash
docker compose up --build  # All 5 services healthy
curl http://localhost:8000/health
docker compose exec postgres psql -U $POSTGRES_USER -d $POSTGRES_DB \
  -c "SELECT COUNT(*) FROM crypto_prices;"
# Row count grows every 60s
```

---

### Build Order Summary

```
Phase 1 → Phase 2 → Phase 3 → Phase 4 → Phase 5 → Phase 6 → Phase 7 → Phase 8
Setup      Schema    Ingest    Worker    API        Alerts    Frontend  Deploy
```

Total: ~45 files across 6 directories (`backend/`, `ingestion/`, `worker/`, `db/`, `frontend/`, root).
Each phase is a shippable increment — do not proceed until its verify step passes.

---

## 12. Phase Progress Tracking

**RULE:** After completing and verifying each phase, update this section immediately before moving to the next phase. This file is the single source of truth for project state.

For each completed phase, record:
1. **Status** — mark complete with ✅, in progress with 🔄, or blocked with ❌
2. **Files created/modified** — every file touched in that phase
3. **Key decisions** — any implementation choices that differed from the original plan and why
4. **Verify result** — actual output of the verify step confirming it passed
5. **Issues encountered** — any bugs or blockers hit and how they were resolved
6. **Next phase notes** — anything the next phase needs to know based on what was just built

**IMPORTANT RULES:**
- Never mark a phase complete without the verify step passing
- Never start the next phase without updating this section first
- If a phase is in progress, mark it as 🔄 In Progress
- If a phase is blocked, mark it as ❌ Blocked and explain why

---

### Phase 1 — Project Setup ⬜
- Status: Not started
- Files created/modified: —
- Key decisions: —
- Verify result: —
- Issues encountered: —
- Next phase notes: —

---

### Phase 2 — Database Layer ⬜
- Status: Not started
- Files created/modified: —
- Key decisions: —
- Verify result: —
- Issues encountered: —
- Next phase notes: —

---

### Phase 3 — Ingestion Layer ⬜
- Status: Not started
- Files created/modified: —
- Key decisions: —
- Verify result: —
- Issues encountered: —
- Next phase notes: —

---

### Phase 4 — Queue Consumer (Worker) ⬜
- Status: Not started
- Files created/modified: —
- Key decisions: —
- Verify result: —
- Issues encountered: —
- Next phase notes: —

---

### Phase 5 — FastAPI Backend ⬜
- Status: Not started
- Files created/modified: —
- Key decisions: —
- Verify result: —
- Issues encountered: —
- Next phase notes: —

---

### Phase 6 — Price Alert System ⬜
- Status: Not started
- Files created/modified: —
- Key decisions: —
- Verify result: —
- Issues encountered: —
- Next phase notes: —

---

### Phase 7 — React Frontend ⬜
- Status: Not started
- Files created/modified: —
- Key decisions: —
- Verify result: —
- Issues encountered: —
- Next phase notes: —

---

### Phase 8 — Deployment ⬜
- Status: Not started
- Files created/modified: —
- Key decisions: —
- Verify result: —
- Issues encountered: —
- Next phase notes: —

---

## 13. MCP Servers & Skills

### MCP Servers — check these are active before each phase

| Server | When to use |
|---|---|
| `filesystem` | All file reads/writes throughout the entire project |
| `github` | Commit progress after each phase is verified. Commit message format: `phase-X: brief description` |
| `context7` | Look up latest docs for any library before implementing it (FastAPI, asyncpg, Redis, TimescaleDB, React Query, Recharts). Always check docs before writing code for a new library. |
| `playwright` | Phase 7 only — test the React frontend in a real browser. Verify price cards load, chart renders, alerts panel works. |
| `chrome-devtools` | Phase 7 only — use alongside playwright to inspect network requests and confirm API calls are returning correct data. |
| `sequential-thinking` | Start of Phase 2, 4, 5, and 6 — before writing any code. These are the complex phases. Use structured reasoning to think through the implementation before touching files. |
| `postgres` | Will be inactive until Docker is running. Use from Phase 2 onwards to verify schema, run queries, and confirm hypertables are set up correctly. |

### Skills — activate before each relevant phase

| Skill | When to activate |
|---|---|
| `swe` | EVERY phase of this build — activate at the start of each phase |
| `simplify` | After Phase 6 is complete — full code review and cleanup pass before moving to the frontend |
| `claude-api` | Not applicable for this project — skip |

### Rules

1. Always use `context7` to check library docs before implementing a new dependency
2. Always use `sequential-thinking` before starting Phase 2, 4, 5, and 6
3. Always commit to `github` after each phase passes its verify step
4. Always run `playwright` tests after Phase 7 is complete
5. Always run the `simplify` skill after Phase 6 before touching the frontend
