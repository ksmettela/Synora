"""Consent management endpoints."""
import uuid
from datetime import datetime
from fastapi import APIRouter, HTTPException, status, Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from db.models import ConsentRecord, DatabaseManager
from models.consent import (
    ConsentRecord as ConsentRecordModel,
    ConsentResponse,
    ConsentStatus,
)
from config import get_settings

router = APIRouter(prefix="/v1/consent", tags=["consent"])


async def get_db_manager() -> DatabaseManager:
    """Get database manager."""
    settings = get_settings()
    return DatabaseManager(settings.DATABASE_URL)


@router.post("/record", response_model=ConsentResponse)
async def record_consent(
    body: ConsentRecordModel,
    db_manager: DatabaseManager = Depends(get_db_manager),
) -> dict:
    """
    Record consent for device.

    GDPR compliance: stores consent timestamp, jurisdiction, and optional TCF string.
    Emits consent.events Kafka message for real-time processing.
    """
    async with db_manager.get_session() as session:
        # Check if record exists
        stmt = select(ConsentRecord).where(ConsentRecord.device_id == body.device_id)
        result = await session.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            # Update existing record
            existing.opted_in = body.opted_in
            existing.consent_timestamp = body.consent_timestamp
            existing.consent_version = body.consent_version
            existing.ip_at_consent = body.ip_at_consent
            existing.jurisdiction = body.jurisdiction
            existing.tcf_string = body.tcf_string
            session.add(existing)
        else:
            # Create new record
            consent_record = ConsentRecord(
                device_id=body.device_id,
                opted_in=body.opted_in,
                consent_timestamp=body.consent_timestamp,
                consent_version=body.consent_version,
                ip_at_consent=body.ip_at_consent,
                jurisdiction=body.jurisdiction,
                tcf_string=body.tcf_string,
            )
            session.add(consent_record)

        await session.commit()

    # In production: emit Kafka event
    # await kafka_producer.send_and_wait(
    #     "consent.events",
    #     {
    #         "device_id": body.device_id,
    #         "opted_in": body.opted_in,
    #         "timestamp": body.consent_timestamp.isoformat(),
    #         "jurisdiction": body.jurisdiction,
    #     }
    # )

    return {
        "device_id": body.device_id,
        "status": "recorded",
        "message": f"Consent recorded for device {body.device_id}",
    }


@router.get("/{device_id}", response_model=ConsentStatus)
async def get_consent(
    device_id: str,
    db_manager: DatabaseManager = Depends(get_db_manager),
) -> dict:
    """Get current consent status for device."""
    async with db_manager.get_session() as session:
        stmt = select(ConsentRecord).where(ConsentRecord.device_id == device_id)
        result = await session.execute(stmt)
        consent = result.scalar_one_or_none()

        if not consent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No consent record found for device {device_id}",
            )

        return {
            "device_id": device_id,
            "opted_in": consent.opted_in,
            "last_updated": consent.updated_at,
            "jurisdiction": consent.jurisdiction,
        }
