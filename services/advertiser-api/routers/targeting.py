"""DSP targeting endpoints."""
import uuid
import time
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException, status, Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert

from db.postgres import (
    Segment,
    SegmentActivation,
    APIUsage,
    DatabaseManager,
)
from models.openrtb import (
    OpenRTBLookupRequest,
    OpenRTBLookupResponse,
    SegmentMatch,
    ActivationRequest,
    ActivationResponse,
    ReachEstimate,
)
from services.redis_service import RedisService
from routers.auth import verify_token
from config import get_settings

router = APIRouter(prefix="/v1/targeting", tags=["targeting"])


async def get_db_manager() -> DatabaseManager:
    """Get database manager."""
    settings = get_settings()
    return DatabaseManager(settings.DATABASE_URL)


async def get_redis_service() -> RedisService:
    """Get Redis service."""
    settings = get_settings()
    return RedisService(settings.REDIS_URL)


def extract_ip_subnet(ip_address: str) -> str:
    """Extract /24 subnet from IP address."""
    parts = ip_address.split(".")
    if len(parts) >= 3:
        return ".".join(parts[:3]) + ".0"
    return ip_address


@router.post("/sync/openrtb", response_model=OpenRTBLookupResponse)
async def device_lookup(
    body: OpenRTBLookupRequest,
    authorization: str = Header(None),
    redis_service: RedisService = Depends(get_redis_service),
) -> dict:
    """
    CRITICAL PATH - Device segment lookup for RTB.

    Must return in <5ms p99. Uses Redis for fast lookup.
    """
    start_time = time.time()

    # Verify token
    if authorization:
        token = authorization.replace("Bearer ", "")
        await verify_token(token, "targeting:read")

    await redis_service.initialize()

    device_id = body.device_id or body.device.ifa if body.device else None
    ip_address = body.ip_address or (body.device.ip if body.device else None)

    matched_segments = []
    cache_hit = False

    # Check Redis hash for device segments
    if device_id:
        segments = await redis_service.get_device_segments(device_id)
        if segments:
            matched_segments = [
                SegmentMatch(
                    segment_id=seg_id, confidence=0.95, source="device_hash"
                )
                for seg_id in segments
            ]
            cache_hit = True

    # If no device_id match, check household lookup by IP subnet
    if not matched_segments and ip_address:
        ip_subnet = extract_ip_subnet(ip_address)
        households = await redis_service.get_household_by_ip(ip_subnet)
        if households:
            # Simulate getting segments for household
            matched_segments = [
                SegmentMatch(
                    segment_id=f"seg_{i}", confidence=0.75, source="ip_household"
                )
                for i in range(min(5, len(households)))
            ]
            cache_hit = True

    lookup_time_ms = (time.time() - start_time) * 1000

    device_id = device_id or "unknown"

    return {
        "device_id": device_id,
        "matched_segments": matched_segments,
        "lookup_time_ms": lookup_time_ms,
        "cache_hit": cache_hit,
    }


@router.post("/activate", response_model=ActivationResponse)
async def activate_targeting(
    body: ActivationRequest,
    authorization: str = Header(None),
    db_manager: DatabaseManager = Depends(get_db_manager),
) -> dict:
    """Activate targeting for segment with CPM floor validation."""
    # Verify token
    if authorization:
        token = authorization.replace("Bearer ", "")
        token_data = await verify_token(token, "targeting:activate")
        client_id = token_data.get("client_id")
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization required",
        )

    activation_id = str(uuid.uuid4())

    async with db_manager.get_session() as session:
        # Get segment to validate CPM floor
        stmt = select(Segment).where(Segment.id == body.segment_id)
        result = await session.execute(stmt)
        segment = result.scalar_one_or_none()

        if not segment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Segment {body.segment_id} not found",
            )

        if body.cpm_floor < segment.minimum_cpm_floor:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"CPM floor {body.cpm_floor} below minimum {segment.minimum_cpm_floor}",
            )

        # Record activation
        activation = SegmentActivation(
            id=activation_id,
            segment_id=body.segment_id,
            client_id=client_id,
            cpm_floor=body.cpm_floor,
            device_count=segment.device_count,
            activated_at=datetime.utcnow(),
        )
        session.add(activation)
        await session.commit()

    return {
        "activation_id": activation_id,
        "segment_id": body.segment_id,
        "status": "activated",
        "activated_at": datetime.utcnow().isoformat(),
    }


@router.get("/reach", response_model=ReachEstimate)
async def estimate_reach(
    segment_id: str,
    authorization: str = Header(None),
    db_manager: DatabaseManager = Depends(get_db_manager),
    redis_service: RedisService = Depends(get_redis_service),
) -> dict:
    """Estimate reach for segment."""
    # Verify token
    if authorization:
        token = authorization.replace("Bearer ", "")
        await verify_token(token, "targeting:read")

    async with db_manager.get_session() as session:
        stmt = select(Segment).where(Segment.id == segment_id)
        result = await session.execute(stmt)
        segment = result.scalar_one_or_none()

        if not segment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Segment {segment_id} not found",
            )

        # Estimate daily impressions (mock: 5 impressions per device daily)
        estimated_daily = segment.device_count * 5

        # Estimate reach percentage (mock)
        reach_percentage = min(
            100.0, (segment.device_count / 50_000_000) * 100
        )  # Assume 50M US households

        return {
            "segment_id": segment_id,
            "household_count": segment.household_count,
            "device_count": segment.device_count,
            "estimated_impressions_daily": estimated_daily,
            "estimated_reach_percentage": reach_percentage,
        }
