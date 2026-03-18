# MarketPulse — Deployment Guide

This guide covers deploying MarketPulse in two modes: **full local stack** (Docker Compose) and **production** (managed services).

---

## Live URLs

| Service | Provider | URL |
|---|---|---|
| Frontend | Vercel | https://market-pulse-rouge.vercel.app |
| Backend | Render | https://marketpulse-h8r7.onrender.com |
| Database | Supabase | aws-1-us-east-1.pooler.supabase.com |
| Redis | Upstash | enabling-gecko-73187.upstash.io (TLS) |

---

## 1. Full Local Stack (Docker Compose)

### Prerequisites

- Docker Desktop installed and running
- `.env` file configured (copy from `.env.example`)

### Steps

```bash
cp .env.example .env
# Edit .env — fill in POSTGRES_USER, POSTGRES_PASSWORD, FINNHUB_API_KEY

docker compose up --build -d

# First time only — run migrations
docker compose exec postgres psql -U $POSTGRES_USER -d $POSTGRES_DB \
  -f /migrations/001_init.sql
docker compose exec postgres psql -U $POSTGRES_USER -d $POSTGRES_DB \
  -f /migrations/002_stock_prices.sql

curl http://localhost:8000/health    # Backend healthy
open http://localhost                # Frontend via nginx
```

### Services

| Service | Port | Description |
|---|---|---|
| postgres | 5432 | TimescaleDB (local only) |
| redis | 6379 | Queue + cache |
| backend | 8000 | FastAPI — serves API + runs ingestion loop |
| frontend | 80 | React dashboard (nginx) |

> **Note:** In production, ingestion runs inside the backend as a background task. Separate `ingestion/` and `worker/` containers are only used locally. Redis is optional in production — the backend writes directly to the database.

---

## 2. Production Deployment

### Architecture

The backend handles everything: it serves the API, fetches prices from CoinGecko and Finnhub, and writes directly to the database. No separate ingestion or worker service is needed.

### Step 1 — Database (Supabase)

1. Create a project at [supabase.com](https://supabase.com)
2. **Do not enable TimescaleDB** — Supabase free tier does not support it. The migrations use standard PostgreSQL only.
3. Run migrations in the SQL editor (Database → SQL Editor):
   - Paste and run `db/migrations/001_init.sql`
   - Paste and run `db/migrations/002_stock_prices.sql`
4. Use the **Session Pooler** connection string (port 5432 on `aws-1-us-east-1.pooler.supabase.com`) — required for Render IPv4 compatibility. Do not use the direct connection or the transaction pooler.

### Step 2 — Redis (Upstash)

1. Create a Redis database at [upstash.com](https://upstash.com)
2. Enable TLS. Set `REDIS_SSL=true` in backend env vars.
3. Copy `REDIS_HOST`, `REDIS_PORT`, `REDIS_PASSWORD`.
4. The backend connects with `username="default"` when SSL is enabled — this is handled automatically via the `redis_ssl` config flag.

### Step 3 — Backend (Render Web Service)

1. Create a **Web Service** on [render.com](https://render.com)
2. Connect your GitHub repo, set root directory to `backend/`
3. **Start Command**: `python main.py` — do not use gunicorn (Render defaults to it for Python, override this manually in Settings)
4. **Port**: `8000`
5. Environment variables:

| Variable | Value |
|---|---|
| `POSTGRES_HOST` | Supabase Session Pooler host |
| `POSTGRES_PORT` | `5432` |
| `POSTGRES_DB` | `postgres` |
| `POSTGRES_USER` | `postgres.xxxx` (Supabase pooler user) |
| `POSTGRES_PASSWORD` | your Supabase password |
| `REDIS_HOST` | Upstash endpoint |
| `REDIS_PORT` | Upstash TLS port |
| `REDIS_PASSWORD` | Upstash password |
| `REDIS_SSL` | `true` |
| `FINNHUB_API_KEY` | your Finnhub key |
| `CORS_ORIGINS` | your Vercel URL (e.g. `https://market-pulse-rouge.vercel.app`) |
| `FETCH_INTERVAL_SECONDS` | `60` |

### Step 4 — Frontend (Vercel)

1. Connect your repo to [vercel.com](https://vercel.com)
2. **Root Directory**: `frontend`
3. **Build Command**: `npm run build`
4. **Output Directory**: `dist`
5. Environment variable: `VITE_API_BASE_URL` = your Render backend URL

**Known Vercel quirks:**
- `frontend/.npmrc` and root `.npmrc` both set `legacy-peer-deps=true` — required due to `@tailwindcss/vite` peer dep conflict
- `vite` is pinned to `^6.3.5` and `@vitejs/plugin-react` to `^4.3.1` — `@tailwindcss/vite@4.2.1` does not support vite v8+
- `VITE_API_BASE_URL` is baked into the JS bundle at build time — changing it requires a redeploy
- If Vercel keeps deploying an old commit, click **Redeploy** and explicitly select the latest commit

### Step 5 — Historical Backfill (optional)

Run locally, pointing at Supabase via env vars:

```bash
cd ingestion
POSTGRES_HOST=... POSTGRES_PASSWORD=... python backfill_stocks.py
POSTGRES_HOST=... POSTGRES_PASSWORD=... python backfill_crypto.py
```

This populates 30 days of historical data so charts are useful immediately after launch.

---

## 3. Environment Variables Reference

| Variable | Default | Used By |
|---|---|---|
| `POSTGRES_HOST` | `localhost` | backend |
| `POSTGRES_PORT` | `5432` | backend |
| `POSTGRES_DB` | — | backend |
| `POSTGRES_USER` | — | backend |
| `POSTGRES_PASSWORD` | — | backend |
| `REDIS_HOST` | `localhost` | backend |
| `REDIS_PORT` | `6379` | backend |
| `REDIS_PASSWORD` | `""` | backend |
| `REDIS_SSL` | `false` | backend |
| `FINNHUB_API_KEY` | `""` | backend (stocks disabled if empty) |
| `FETCH_INTERVAL_SECONDS` | `60` | backend |
| `CORS_ORIGINS` | `http://localhost:5173` | backend |
| `VITE_API_BASE_URL` | `http://localhost:8000` | frontend (build-time) |

---

## 4. Troubleshooting

| Issue | Solution |
|---|---|
| Render defaults to gunicorn | Set Start Command to `python main.py` in Render Settings |
| Render service "Timed Out" / no port detected | Render Web Services require an open HTTP port. Backend binds port 8000 automatically |
| Render shows "In Progress" permanently | Normal — the process is running. Render only shows "Live" for services with active HTTP traffic |
| Render free tier spins down | First request after inactivity takes ~50s to wake. This is expected |
| 7d/30d charts fail to load | `time_bucket()` is TimescaleDB-only and not available on Supabase free tier. The codebase uses `date_trunc()` instead — do not reintroduce `time_bucket` |
| Crypto cards show "—" for price change % | Recent rows from CoinGecko may have `price_change_24h = NULL`. The SQL uses COALESCE to fall back to the most recent non-null value |
| Stock chart shows a spike at the start of live data | yfinance backfill prices differ from Finnhub live prices. The 24h view uses 1h bucketing to average out the discrepancy |
| CoinGecko 429 errors in backend logs | Rate limit on free tier. Ingestion skips the cycle and retries next interval — this is normal and handled |
| Frontend shows "Failed to load prices" | Check backend is running and `VITE_API_BASE_URL` points to the correct Render URL |
| Supabase TimescaleDB extension error | Do not enable TimescaleDB on Supabase free tier. Run migrations without hypertable calls |
| Redis auth error with Upstash TLS | Set `REDIS_SSL=true`. The backend automatically sets `username="default"` when SSL is enabled |
