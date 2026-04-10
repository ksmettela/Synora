"""Reporting and analytics endpoints."""
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, HTTPException, status, Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from db.postgres import SegmentActivation, DatabaseManager
from services.redis_service import RedisService
from routers.auth import verify_token
from config import get_settings

router = APIRouter(prefix="/v1/reports", tags=["reports"])


async def get_db_manager() -> DatabaseManager:
    """Get database manager."""
    settings = get_settings()
    return DatabaseManager(settings.DATABASE_URL)


async def get_redis_service() -> RedisService:
    """Get Redis service."""
    settings = get_settings()
    return RedisService(settings.REDIS_URL)


@router.get("/delivery")
async def delivery_stats(
    segment_id: Optional[str] = None,
    days: int = 7,
    authorization: str = Header(None),
    db_manager: DatabaseManager = Depends(get_db_manager),
) -> dict:
    """Get delivery statistics for segment."""
    # Verify token
    if authorization:
        token = authorization.replace("Bearer ", "")
        await verify_token(token, "reports:read")

    async with db_manager.get_session() as session:
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        stmt = select(SegmentActivation).where(
            SegmentActivation.activated_at >= cutoff_date
        )

        if segment_id:
            stmt = stmt.where(SegmentActivation.segment_id == segment_id)

        result = await session.execute(stmt)
        activations = result.scalars().all()

        total_device_count = sum(a.device_count for a in activations)
        total_activations = len(activations)
        avg_cpm = (
            sum(a.cpm_floor for a in activations) / len(activations)
            if activations
            else 0
        )

        return {
            "segment_id": segment_id,
            "period_days": days,
            "total_activations": total_activations,
            "total_device_count": total_device_count,
            "average_cpm": avg_cpm,
            "report_timestamp": datetime.utcnow().isoformat(),
        }


@router.get("/overlap")
async def segment_overlap(
    segment_ids: list[str],
    authorization: str = Header(None),
    redis_service: RedisService = Depends(get_redis_service),
) -> dict:
    """Calculate segment overlap using Redis SINTERCARD."""
    # Verify token
    if authorization:
        token = authorization.replace("Bearer ", "")
        await verify_token(token, "reports:read")

    if len(segment_ids) < 2:
        return {
            "segments": segment_ids,
            "overlap_count": 0,
            "message": "Need at least 2 segments for overlap analysis",
        }

    await redis_service.initialize()

    # Get intersection cardinality using Redis SINTERCARD
    overlap_count = await redis_service.get_segment_intersection_count(segment_ids)

    return {
        "segments": segment_ids,
        "overlap_count": overlap_count,
        "report_timestamp": datetime.utcnow().isoformat(),
    }
