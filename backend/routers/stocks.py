import json
import logging
from datetime import datetime
from typing import Annotated, Optional

import asyncpg
import redis.asyncio as aioredis
from fastapi import APIRouter, HTTPException, Query, Request

from models.db import StockPrice
from models.responses import APIResponse
from services import cache as cache_svc
from services import db as db_svc

logger = logging.getLogger(__name__)
router = APIRouter()


def _pool(request: Request) -> asyncpg.Pool:
    return request.app.state.pool


def _redis(request: Request) -> aioredis.Redis:
    return request.app.state.redis


def _serialise(items: list) -> str:
    return json.dumps([i.model_dump(mode="json") for i in items])


@router.get("/stocks/latest", response_model=APIResponse[list[StockPrice]])
async def get_latest_stocks(request: Request) -> APIResponse[list[StockPrice]]:
    pool = _pool(request)
    redis = _redis(request)
    cache_key = "cache:stocks:latest"

    cached = await cache_svc.get_cached(redis, cache_key)
    if cached:
        return APIResponse(data=json.loads(cached))

    stocks = await db_svc.get_latest_stocks(pool)
    await cache_svc.set_cached(redis, cache_key, _serialise(stocks), ttl=60)
    return APIResponse(data=stocks)


@router.get("/stocks/{symbol}/history", response_model=APIResponse[list[StockPrice]])
async def get_stock_history(
    symbol: str,
    request: Request,
    from_time: Annotated[datetime, Query(alias="from")],
    to_time: Annotated[datetime, Query(alias="to")],
    interval: Annotated[Optional[str], Query()] = None,
) -> APIResponse[list[StockPrice]]:
    if interval is not None and interval not in ("1h", "1d"):
        raise HTTPException(status_code=422, detail="interval must be '1h' or '1d'")
    if from_time >= to_time:
        raise HTTPException(status_code=422, detail="'from' must be earlier than 'to'")

    pool = _pool(request)
    redis = _redis(request)
    cache_key = f"cache:stocks:history:{symbol.lower()}:{from_time.isoformat()}:{to_time.isoformat()}"
    if interval:
        cache_key += f":{interval}"

    cached = await cache_svc.get_cached(redis, cache_key)
    if cached:
        return APIResponse(data=json.loads(cached))

    history = await db_svc.get_stock_history(pool, symbol.lower(), from_time, to_time, interval)
    await cache_svc.set_cached(redis, cache_key, _serialise(history), ttl=60)
    return APIResponse(data=history)
