# MarketPulse — Deployment Guide

This guide covers deploying MarketPulse in two modes: **full local stack** (all services via Docker Compose) and **production** (managed services).

---

## 1. Full Local Stack (Docker Compose)

Run all 6 services locally with a single command.

### Prerequisites

- Docker Desktop installed and running
- `.env` file configured (copy from `.env.example`)

### Steps

```bash
# 1. Clone and configure
cp .env.example .env
# Edit .env — fill in POSTGRES_USER, POSTGRES_PASSWORD, FINNHUB_API_KEY

# 2. Start everything
docker compose up --build -d

# 3. Run database migrations (first time only)
docker compose exec postgres psql -U $POSTGRES_USER -d $POSTGRES_DB \
  -c "CREATE EXTENSION IF NOT EXISTS timescaledb;"
docker compose exec postgres psql -U $POSTGRES_USER -d $POSTGRES_DB \
  -f /migrations/001_init.sql
docker compose exec postgres psql -U $POSTGRES_USER -d $POSTGRES_DB \
  -f /migrations/002_stock_prices.sql

# 4. Verify
docker compose ps                          # All 6 services running
curl http://localhost:8000/health           # Backend healthy
open http://localhost                       # Frontend via nginx on port 80
```

### Services

| Service | Port | Description |
|---|---|---|
| postgres | 5432 | TimescaleDB (data storage) |
| redis | 6379 | Queue + cache |
| backend | 8000 | FastAPI REST API |
| ingestion | — | CoinGecko + Finnhub fetcher |
| worker | — | Queue consumer → DB writer |
| frontend | 80 | React dashboard (nginx) |

### Useful Commands

```bash
docker compose logs -f backend         # Stream backend logs
docker compose logs -f ingestion       # Stream ingestion logs
docker compose restart backend         # Restart a single service
docker compose down                    # Stop all (keeps data)
docker compose down -v                 # Stop all + DELETE data
```

---

## 2. Production Deployment

Recommended production stack:

| Component | Provider | Why |
|---|---|---|
| Database | **Supabase** | Managed PostgreSQL with TimescaleDB extension support |
| Redis | **Upstash** | Serverless Redis, free tier available |
| Backend + Ingestion + Worker | **Render** | Docker-based web services |
| Frontend | **Vercel** | Static site hosting from `frontend/dist` |

### Step 1 — Database (Supabase)

1. Create a project at [supabase.com](https://supabase.com)
2. Enable TimescaleDB: go to **Database → Extensions** and enable `timescaledb`
3. Run migrations in the SQL editor:
   - Paste contents of `db/migrations/001_init.sql`
   - Paste contents of `db/migrations/002_stock_prices.sql`
4. Copy connection details:
   - `POSTGRES_HOST` — your Supabase host (e.g. `db.xxxx.supabase.co`)
   - `POSTGRES_PORT` — `5432` (or `6543` for connection pooling)
   - `POSTGRES_DB` — `postgres`
   - `POSTGRES_USER` — `postgres`
   - `POSTGRES_PASSWORD` — your project password

### Step 2 — Redis (Upstash)

1. Create a Redis database at [upstash.com](https://upstash.com)
2. Copy connection details:
   - `REDIS_HOST` — your Upstash endpoint
   - `REDIS_PORT` — `6379` (or the TLS port)
   - `REDIS_PASSWORD` — your Upstash password

### Step 3 — Backend, Ingestion, Worker (Render)

Create 3 separate **Web Services** (or Background Workers) on [render.com](https://render.com):

#### Backend (Web Service)

- **Docker**: point to `backend/` directory
- **Port**: `8000`
- **Environment variables**: all `POSTGRES_*`, `REDIS_*`, `CORS_ORIGINS` (set to your Vercel URL)

#### Ingestion (Background Worker)

- **Docker**: point to `ingestion/` directory
- **Environment variables**: `REDIS_*`, `FINNHUB_API_KEY`

#### Worker (Background Worker)

- **Docker**: point to `worker/` directory
- **Environment variables**: `REDIS_*`, `POSTGRES_*`

### Step 4 — Frontend (Vercel)

1. Connect your repo to [vercel.com](https://vercel.com)
2. Set the root directory to `frontend`
3. Build command: `npm run build`
4. Output directory: `dist`
5. Environment variable: `VITE_API_BASE_URL` = your Render backend URL (e.g. `https://marketpulse-api.onrender.com`)

### Step 5 — Verify

1. Check Render backend: `curl https://your-backend.onrender.com/health`
2. Open your Vercel URL — dashboard should load with live data
3. Check Render logs for ingestion and worker — data should be flowing

---

## 3. Environment Variables Reference

| Variable | Required | Default | Used By |
|---|---|---|---|
| `POSTGRES_HOST` | Yes | `localhost` | backend, worker |
| `POSTGRES_PORT` | No | `5432` | backend, worker |
| `POSTGRES_DB` | Yes | — | backend, worker |
| `POSTGRES_USER` | Yes | — | backend, worker |
| `POSTGRES_PASSWORD` | Yes | — | backend, worker |
| `REDIS_HOST` | Yes | `localhost` | backend, ingestion, worker |
| `REDIS_PORT` | No | `6379` | backend, ingestion, worker |
| `REDIS_PASSWORD` | No | `""` | backend, ingestion, worker |
| `FINNHUB_API_KEY` | No | `""` | ingestion (stocks disabled if empty) |
| `CORS_ORIGINS` | No | `http://localhost:5173` | backend |
| `VITE_API_BASE_URL` | No | `http://localhost:8000` | frontend (build-time) |

---

## 4. Troubleshooting

| Issue | Solution |
|---|---|
| No stock data | Set `FINNHUB_API_KEY` in `.env` and restart ingestion |
| Frontend shows "Failed to load prices" | Check backend is running and `VITE_API_BASE_URL` is correct |
| Empty charts on 7d/30d | Data needs time to accumulate — only shows data from when ingestion started |
| TimescaleDB extension error | Run `CREATE EXTENSION IF NOT EXISTS timescaledb;` in your database |
| Redis connection refused | Check `REDIS_HOST` and `REDIS_PASSWORD` are correct |
