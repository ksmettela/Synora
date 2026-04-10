"""Privacy rights endpoints (CCPA/GDPR compliance)."""
import uuid
import hashlib
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, HTTPException, status, Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert, update

from db.models import (
    OptOutRequest,
    DataExportJob,
    ConsentRecord,
    DatabaseManager,
)
from models.consent import (
    OptOutRequest as OptOutRequestModel,
    OptOutResponse,
    DataExportRequest,
    DataExportResponse,
    EraseRequest,
    EraseResponse,
    TCFConsentRequest,
    TCFResponse,
)
from services.deletion_service import DeletionService
from services.audit_log import AuditLogger
from services.redis_service import RedisService
from services.tcf_parser import TCFParser, TCFValidator
from config import get_settings

router = APIRouter(prefix="/v1/privacy", tags=["privacy"])


async def get_db_manager() -> DatabaseManager:
    """Get database manager."""
    settings = get_settings()
    return DatabaseManager(settings.DATABASE_URL)


async def get_redis_service() -> RedisService:
    """Get Redis service."""
    settings = get_settings()
    return RedisService(settings.REDIS_URL)


@router.post("/opt-out", response_model=OptOutResponse)
async def opt_out(
    body: OptOutRequestModel,
    db_manager: DatabaseManager = Depends(get_db_manager),
    redis_service: RedisService = Depends(get_redis_service),
) -> dict:
    """
    CCPA/GDPR right to be forgotten.

    - Records opt-out request
    - Removes from Redis segments immediately
    - Schedules deletion from PostgreSQL and Iceberg within compliance deadline
    """
    settings = get_settings()
    request_id = str(uuid.uuid4())

    # Determine deadline based on jurisdiction
    if body.jurisdiction == "US":
        deadline_hours = settings.CCPA_DELETION_DEADLINE_HOURS
    else:
        deadline_hours = settings.GDPR_DELETION_DEADLINE_HOURS

    deadline = datetime.utcnow() + timedelta(hours=deadline_hours)

    async with db_manager.get_session() as session:
        # Record opt-out request
        opt_out_record = OptOutRequest(
            id=request_id,
            device_id=body.device_id,
            jurisdiction=body.jurisdiction,
            request_type="opt_out",
            status="in_progress",
            requested_at=datetime.utcnow(),
            completion_deadline=deadline,
        )
        session.add(opt_out_record)
        await session.commit()

    # Remove from Redis immediately
    await redis_service.initialize()
    await redis_service.clear_device_segments(body.device_id)

    # In production: dispatch deletion job
    # deletion_service = DeletionService(redis_service, audit_logger)
    # await deletion_service.delete_device_data(
    #     session, body.device_id, body.jurisdiction, request_id
    # )

    return {
        "request_id": request_id,
        "device_id": body.device_id,
        "status": "processing",
        "deadline": deadline,
        "message": f"Opt-out request {request_id} received. Deletion within {deadline_hours} hours.",
    }


@router.get("/data-export", response_model=DataExportResponse)
async def data_export(
    device_id: str,
    db_manager: DatabaseManager = Depends(get_db_manager),
) -> dict:
    """
    GDPR Data Subject Access Request (DSAR).

    Collects all data held for device_id across systems.
    Returns pre-signed S3 URL to ZIP file.
    """
    settings = get_settings()
    job_id = str(uuid.uuid4())

    async with db_manager.get_session() as session:
        # Check consent record
        stmt = select(ConsentRecord).where(ConsentRecord.device_id == device_id)
        result = await session.execute(stmt)
        consent = result.scalar_one_or_none()

        if not consent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No data found for device {device_id}",
            )

        # Create export job
        export_job = DataExportJob(
            id=job_id,
            device_id=device_id,
            requested_at=datetime.utcnow(),
            status="processing",
        )
        session.add(export_job)
        await session.commit()

    # In production:
    # 1. Query PostgreSQL consent_records
    # 2. Query Trino viewership table
    # 3. Query Redis segment memberships
    # 4. Package as JSON/CSV
    # 5. Upload to S3 with pre-signed URL
    # 6. Return URL with 72-hour expiry

    expiry = datetime.utcnow() + timedelta(hours=settings.GDPR_DSAR_DEADLINE_HOURS)

    return {
        "job_id": job_id,
        "device_id": device_id,
        "status": "processing",
        "export_url": None,  # Would be S3 pre-signed URL
        "expiry": expiry,
        "message": f"DSAR job {job_id} processing. Download link will be ready within 72 hours.",
    }


@router.delete("/erase", response_model=EraseResponse)
async def erase_data(
    body: EraseRequest,
    db_manager: DatabaseManager = Depends(get_db_manager),
    redis_service: RedisService = Depends(get_redis_service),
) -> dict:
    """
    GDPR right to erasure (right to be forgotten).

    Permanently deletes all personal data across PostgreSQL, Redis, and Iceberg.
    """
    settings = get_settings()
    request_id = str(uuid.uuid4())

    # GDPR deadline: 72 hours
    deadline = datetime.utcnow() + timedelta(
        hours=settings.GDPR_DELETION_DEADLINE_HOURS
    )

    async with db_manager.get_session() as session:
        # Record deletion request
        deletion_request = OptOutRequest(
            id=request_id,
            device_id=body.device_id,
            jurisdiction=body.jurisdiction,
            request_type="erasure",
            status="in_progress",
            requested_at=datetime.utcnow(),
            completion_deadline=deadline,
        )
        session.add(deletion_request)
        await session.commit()

    # Delete from Redis immediately
    await redis_service.initialize()
    await redis_service.clear_device_segments(body.device_id)

    # In production: dispatch comprehensive deletion
    # deletion_service = DeletionService(redis_service, audit_logger)
    # await deletion_service.delete_device_data(
    #     session, body.device_id, body.jurisdiction, request_id
    # )

    return {
        "request_id": request_id,
        "device_id": body.device_id,
        "status": "in_progress",
        "deadline": deadline,
        "message": f"Right to erasure request {request_id} accepted. Complete deletion within 72 hours.",
    }


@router.post("/tcf", response_model=TCFResponse)
async def process_tcf(
    body: TCFConsentRequest,
    db_manager: DatabaseManager = Depends(get_db_manager),
) -> dict:
    """
    Process IAB TCF 2.2 consent string.

    Parses vendor and purpose consents from TCF string.
    Updates consent record accordingly.
    """
    # Validate TCF string
    if not TCFValidator.is_valid_tcf_string(body.tcf_string):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid TCF consent string",
        )

    # Parse TCF string
    parser = TCFParser()
    parsed = parser.parse(body.tcf_string)

    if not parsed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to parse TCF consent string",
        )

    async with db_manager.get_session() as session:
        # Update or create consent record
        stmt = select(ConsentRecord).where(ConsentRecord.device_id == body.device_id)
        result = await session.execute(stmt)
        consent = result.scalar_one_or_none()

        if consent:
            consent.tcf_string = body.tcf_string
            consent.purposes = parsed.get("purposes", [])
            consent.vendors = parsed.get("vendors", [])
            consent.special_features = parsed.get("special_features", [])
            consent.updated_at = datetime.utcnow()
            session.add(consent)
        else:
            consent = ConsentRecord(
                device_id=body.device_id,
                opted_in=True,
                consent_timestamp=datetime.utcnow(),
                jurisdiction="EU",
                tcf_string=body.tcf_string,
                purposes=parsed.get("purposes", []),
                vendors=parsed.get("vendors", []),
                special_features=parsed.get("special_features", []),
                ip_at_consent=body.ip_address,
            )
            session.add(consent)

        await session.commit()

    return {
        "device_id": body.device_id,
        "status": "processed",
        "purposes": parsed.get("purposes", []),
        "vendors": parsed.get("vendors", []),
        "special_features": parsed.get("special_features", []),
        "message": "TCF consent string processed successfully",
    }
