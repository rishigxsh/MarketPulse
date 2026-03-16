import json
import logging
from datetime import datetime
from typing import Annotated, Literal, Optional

import asyncpg
import redis.asyncio as aioredis
from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, field_validator

from models.db import CryptoPrice, PriceAlert
from models.responses import APIResponse
from services import cache as cache_svc
from services import db as db_svc

logger = logging.getLogger(__name__)
router = APIRouter()


# ---------------------------------------------------------------------------
# Dependencies — pull pool and redis off app.state
# ---------------------------------------------------------------------------

def _pool(request: Request) -> asyncpg.Pool:
    return request.app.state.pool


def _redis(request: Request) -> aioredis.Redis:
    return request.app.state.redis


# ---------------------------------------------------------------------------
# Request body models
# ---------------------------------------------------------------------------

class CreateAlertRequest(BaseModel):
    symbol: str
    target_price: float
    direction: Literal["above", "below"]

    @field_validator("symbol")
    @classmethod
    def normalise_symbol(cls, v: str) -> str:
        return v.lower().strip()

    @field_validator("target_price")
    @classmethod
    def validate_price(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("target_price must be greater than zero")
        return v


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _serialise(items: list) -> str:
    return json.dumps([i.model_dump(mode="json") for i in items])


# ---------------------------------------------------------------------------
# Price endpoints
# ---------------------------------------------------------------------------

@router.get("/prices/latest", response_model=APIResponse[list[CryptoPrice]])
async def get_latest_prices(request: Request) -> APIResponse[list[CryptoPrice]]:
    pool = _pool(request)
    redis = _redis(request)
    cache_key = "cache:latest"

    cached = await cache_svc.get_cached(redis, cache_key)
    if cached:
        return APIResponse(data=json.loads(cached))

    prices = await db_svc.get_latest_prices(pool)
    await cache_svc.set_cached(redis, cache_key, _serialise(prices), ttl=60)
    return APIResponse(data=prices)


@router.get("/prices/{symbol}/history", response_model=APIResponse[list[CryptoPrice]])
async def get_price_history(
    symbol: str,
    request: Request,
    from_time: Annotated[datetime, Query(alias="from")],
    to_time: Annotated[datetime, Query(alias="to")],
    interval: Annotated[Optional[str], Query()] = None,
) -> APIResponse[list[CryptoPrice]]:
    if interval is not None and interval not in ("1h", "1d"):
        raise HTTPException(status_code=422, detail="interval must be '1h' or '1d'")
    if from_time >= to_time:
        raise HTTPException(status_code=422, detail="'from' must be earlier than 'to'")

    pool = _pool(request)
    redis = _redis(request)
    cache_key = f"cache:history:{symbol.lower()}:{from_time.isoformat()}:{to_time.isoformat()}"
    if interval:
        cache_key += f":{interval}"

    cached = await cache_svc.get_cached(redis, cache_key)
    if cached:
        return APIResponse(data=json.loads(cached))

    history = await db_svc.get_price_history(pool, symbol.lower(), from_time, to_time, interval)
    await cache_svc.set_cached(redis, cache_key, _serialise(history), ttl=60)
    return APIResponse(data=history)


# ---------------------------------------------------------------------------
# Alert endpoints
# ---------------------------------------------------------------------------

@router.post("/alerts", response_model=APIResponse[PriceAlert], status_code=201)
async def create_alert(
    body: CreateAlertRequest,
    request: Request,
) -> APIResponse[PriceAlert]:
    pool = _pool(request)
    alert = await db_svc.create_alert(pool, body.symbol, body.target_price, body.direction)
    logger.info("Alert created: id=%d %s %s %.8f", alert.id, alert.symbol, alert.direction, alert.target_price)
    return APIResponse(data=alert)


@router.get("/alerts", response_model=APIResponse[list[PriceAlert]])
async def get_alerts(request: Request) -> APIResponse[list[PriceAlert]]:
    pool = _pool(request)
    alerts = await db_svc.get_alerts(pool)
    return APIResponse(data=alerts)


@router.get("/alerts/triggered", response_model=APIResponse[list[PriceAlert]])
async def get_triggered_alerts(request: Request) -> APIResponse[list[PriceAlert]]:
    pool = _pool(request)
    alerts = await db_svc.get_triggered_alerts(pool)
    return APIResponse(data=alerts)


@router.delete("/alerts/{alert_id}", response_model=APIResponse[None])
async def delete_alert(alert_id: int, request: Request) -> APIResponse[None]:
    pool = _pool(request)
    deleted = await db_svc.delete_alert(pool, alert_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")
    logger.info("Alert deleted: id=%d", alert_id)
    return APIResponse(data=None)
