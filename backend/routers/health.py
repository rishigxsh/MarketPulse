import logging
from datetime import datetime, timezone

from fastapi import APIRouter

from models.responses import APIResponse

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/health", response_model=APIResponse[dict])
async def health_check() -> APIResponse[dict]:
    logger.info("Health check requested")
    return APIResponse(data={"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()})
