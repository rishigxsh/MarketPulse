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


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("MarketPulse backend starting up")

    # --- asyncpg connection pool ---
    app.state.pool = await asyncpg.create_pool(
        dsn=settings.postgres_dsn,
        min_size=2,
        max_size=10,
        command_timeout=30,
    )
    logger.info("TimescaleDB connection pool created")

    # --- Redis async client ---
    app.state.redis = aioredis.Redis(
        host=settings.redis_host,
        port=settings.redis_port,
        password=settings.redis_password or None,
        decode_responses=True,
        ssl=settings.redis_ssl,
    )
    await app.state.redis.ping()
    logger.info("Redis connection OK")

    # --- Alert background task ---
    task = asyncio.create_task(_alert_loop(app.state.pool))

    yield

    task.cancel()
    try:
        await task
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
