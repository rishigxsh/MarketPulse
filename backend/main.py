import asyncio
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import asyncpg
import redis.asyncio as aioredis
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from config import settings
from models.responses import APIResponse
from routers import health, prices, stocks
from services.alerts import check_alerts
from services.ingestion import run_ingestion_cycle

ALERT_CHECK_INTERVAL = 30  # seconds

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def _alert_loop(pool: asyncpg.Pool) -> None:
    """Background task: check price alerts on a fixed interval."""
    logger.info("Alert check loop started (interval=%ds)", ALERT_CHECK_INTERVAL)
    while True:
        await asyncio.sleep(ALERT_CHECK_INTERVAL)
        triggered = await check_alerts(pool)
        if triggered:
            logger.info("Alert loop: %d alert(s) triggered this cycle", len(triggered))


async def _ingestion_loop(pool: asyncpg.Pool) -> None:
    """Background task: fetch prices and write to DB every FETCH_INTERVAL_SECONDS."""
    logger.info("Ingestion loop started (interval=%ds)", settings.fetch_interval_seconds)
    while True:
        try:
            await run_ingestion_cycle(pool)
        except Exception as e:
            logger.error("Ingestion cycle error: %s", e)
        await asyncio.sleep(settings.fetch_interval_seconds)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("MarketPulse backend starting up")

    # --- asyncpg connection pool ---
    logger.info(
        "Connecting to PostgreSQL: host=%s port=%s db=%s user=%s pass=%s",
        settings.postgres_host, settings.postgres_port,
        settings.postgres_db, settings.postgres_user,
        settings.postgres_password[:4] + "****" if settings.postgres_password else "EMPTY",
    )
    app.state.pool = await asyncpg.create_pool(
        host=settings.postgres_host,
        port=settings.postgres_port,
        database=settings.postgres_db,
        user=settings.postgres_user,
        password=settings.postgres_password,
        min_size=2,
        max_size=10,
        command_timeout=30,
    )
    logger.info("TimescaleDB connection pool created")

    # --- Redis async client ---
    app.state.redis = aioredis.Redis(
        host=settings.redis_host,
        port=settings.redis_port,
        username="default" if settings.redis_ssl else None,
        password=settings.redis_password or None,
        decode_responses=True,
        ssl=settings.redis_ssl,
    )
    await app.state.redis.ping()
    logger.info("Redis connection OK")

    # --- Background tasks ---
    alert_task = asyncio.create_task(_alert_loop(app.state.pool))
    ingestion_task = asyncio.create_task(_ingestion_loop(app.state.pool))

    yield

    alert_task.cancel()
    ingestion_task.cancel()
    for t in (alert_task, ingestion_task):
        try:
            await t
        except asyncio.CancelledError:
            pass

    # --- Graceful shutdown ---
    await app.state.pool.close()
    await app.state.redis.aclose()
    logger.info("MarketPulse backend shut down cleanly")


app = FastAPI(
    title="MarketPulse API",
    description="Real-time crypto market data pipeline API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error("Unhandled exception on %s %s: %s", request.method, request.url, exc)
    return JSONResponse(
        status_code=500,
        content=APIResponse(error=str(exc)).model_dump(),
    )


app.include_router(health.router)
app.include_router(prices.router)
app.include_router(stocks.router)
