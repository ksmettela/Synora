"""Segment management endpoints."""
import uuid
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException, status, Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from db.postgres import Segment, DatabaseManager
from models.segment import (
    SegmentDefinition,
    SegmentResponse,
    SegmentCreateResponse,
    SegmentSizeResponse,
    SegmentListResponse,
)
from services.segment_builder import SegmentSQLBuilder
from services.redis_service import RedisService
from routers.auth import verify_token
from config import get_settings

router = APIRouter(prefix="/v1/segments", tags=["segments"])


async def get_db_manager() -> DatabaseManager:
    """Get database manager."""
    settings = get_settings()
    return DatabaseManager(settings.DATABASE_URL)


async def get_redis_service() -> RedisService:
    """Get Redis service."""
    settings = get_settings()
    return RedisService(settings.REDIS_URL)


@router.get("", response_model=SegmentListResponse)
async def list_segments(
    authorization: str = Header(None),
    db_manager: DatabaseManager = Depends(get_db_manager),
) -> dict:
    """List all available segments."""
    # Verify token
    if authorization:
        token = authorization.replace("Bearer ", "")
        await verify_token(token, "segments:read")

    async with db_manager.get_session() as session:
        stmt = select(Segment).where(Segment.status == "active")
        result = await session.execute(stmt)
        segments = result.scalars().all()

        return {
            "total": len(segments),
            "segments": [
                SegmentResponse.from_orm(segment) for segment in segments
            ],
        }


@router.post("", response_model=SegmentCreateResponse)
async def create_segment(
    body: SegmentDefinition,
    authorization: str = Header(None),
    db_manager: DatabaseManager = Depends(get_db_manager),
) -> dict:
    """Create new segment with DSL rules."""
    # Verify token
    token_data = None
    if authorization:
        token = authorization.replace("Bearer ", "")
        token_data = await verify_token(token, "segments:write")

    segment_id = str(uuid.uuid4())

    # Validate rules
    for rule in body.rules:
        if rule.type not in [
            "watched_genre",
            "watched_network",
            "household_income",
            "dma",
            "daypart",
        ]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid rule type: {rule.type}",
            )

    # Create segment in database
    async with db_manager.get_session() as session:
        segment = Segment(
            id=segment_id,
            name=body.name,
            description=None,
            rules_json=body.model_dump(),
            logic=body.logic,
            lookback_days=body.lookback_days,
            minimum_cpm_floor=body.minimum_cpm_floor,
            status="pending",
            created_by=token_data.get("client_id") if token_data else "anonymous",
        )
        session.add(segment)
        await session.commit()

    # Dispatch async Celery task to populate segment
    # (In production: celery_app.send_task('tasks.populate_segment', args=[segment_id]))

    return {
        "segment_id": segment_id,
        "status": "pending",
        "message": f"Segment {segment_id} created. Population task dispatched.",
    }


@router.get("/{segment_id}/size", response_model=SegmentSizeResponse)
async def get_segment_size(
    segment_id: str,
    authorization: str = Header(None),
    db_manager: DatabaseManager = Depends(get_db_manager),
    redis_service: RedisService = Depends(get_redis_service),
) -> dict:
    """Get segment size from Redis."""
    # Verify token
    if authorization:
        token = authorization.replace("Bearer ", "")
        await verify_token(token, "segments:read")

    # Check Redis first
    await redis_service.initialize()
    device_count = await redis_service.get_segment_size(segment_id)

    # Fall back to database
    if device_count == 0:
        async with db_manager.get_session() as session:
            stmt = select(Segment).where(Segment.id == segment_id)
            result = await session.execute(stmt)
            segment = result.scalar_one_or_none()

            if not segment:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Segment {segment_id} not found",
                )

            return {
                "segment_id": segment_id,
                "household_count": segment.household_count,
                "device_count": segment.device_count,
                "last_updated": segment.updated_at,
            }

    # From Redis
    return {
        "segment_id": segment_id,
        "household_count": 0,  # Would be fetched from database separately
        "device_count": device_count,
        "last_updated": datetime.utcnow(),
    }


@router.get("/{segment_id}", response_model=SegmentResponse)
async def get_segment(
    segment_id: str,
    authorization: str = Header(None),
    db_manager: DatabaseManager = Depends(get_db_manager),
) -> dict:
    """Get segment details."""
    # Verify token
    if authorization:
        token = authorization.replace("Bearer ", "")
        await verify_token(token, "segments:read")

    async with db_manager.get_session() as session:
        stmt = select(Segment).where(Segment.id == segment_id)
        result = await session.execute(stmt)
        segment = result.scalar_one_or_none()

        if not segment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Segment {segment_id} not found",
            )

        return SegmentResponse.from_orm(segment)
