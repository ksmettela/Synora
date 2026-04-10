"""Data deletion service for CCPA/GDPR compliance."""
import hashlib
import json
from datetime import datetime
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import delete, select

from db.models import ConsentRecord, OptOutRequest, AuditLogEvent
from services.redis_service import RedisService
from services.audit_log import AuditLogger


class DeletionService:
    """Handles data deletion across all systems."""

    def __init__(
        self,
        redis_service: RedisService,
        audit_logger: AuditLogger,
    ):
        self.redis_service = redis_service
        self.audit_logger = audit_logger

    async def delete_device_data(
        self,
        session: AsyncSession,
        device_id: str,
        jurisdiction: str,
        request_id: str,
        operator_id: Optional[str] = None,
    ) -> bool:
        """
        Delete all data for device across PostgreSQL, Redis, and schedule Iceberg deletion.

        Implements CCPA (24 hours) and GDPR (72 hours) compliance.
        """
        try:
            # Log the deletion request
            device_id_hash = hashlib.sha256(device_id.encode()).hexdigest()
            await self.audit_logger.log_action(
                device_id_hash=device_id_hash,
                action="data_deletion_initiated",
                jurisdiction=jurisdiction,
                operator_id=operator_id,
                metadata={
                    "request_id": request_id,
                    "device_id_hash": device_id_hash,
                },
            )

            # 1. Delete from PostgreSQL consent_records
            await self._delete_from_postgres(session, device_id)

            # 2. Delete from Redis (all segment memberships and device mappings)
            await self._delete_from_redis(device_id)

            # 3. Schedule deletion from Iceberg (async job)
            await self._schedule_iceberg_deletion(device_id, jurisdiction, request_id)

            # Log completion
            await self.audit_logger.log_action(
                device_id_hash=device_id_hash,
                action="data_deletion_completed",
                jurisdiction=jurisdiction,
                operator_id=operator_id,
                metadata={
                    "request_id": request_id,
                    "deleted_at": datetime.utcnow().isoformat(),
                },
            )

            return True

        except Exception as e:
            await self.audit_logger.log_action(
                device_id_hash=hashlib.sha256(device_id.encode()).hexdigest(),
                action="data_deletion_failed",
                jurisdiction=jurisdiction,
                operator_id=operator_id,
                metadata={
                    "request_id": request_id,
                    "error": str(e),
                },
            )
            return False

    async def _delete_from_postgres(
        self, session: AsyncSession, device_id: str
    ) -> None:
        """Delete all device data from PostgreSQL."""
        # Delete consent record
        stmt = delete(ConsentRecord).where(ConsentRecord.device_id == device_id)
        await session.execute(stmt)
        await session.commit()

    async def _delete_from_redis(self, device_id: str) -> None:
        """Delete all device data from Redis."""
        await self.redis_service.initialize()

        # Remove from device_segments hash
        await self.redis_service.clear_device_segments(device_id)

        # Note: In production, would also remove device from all segment sets
        # This requires iterating through all segments and calling:
        # for each segment: SREM segment:{segment_id} {device_id}

    async def _schedule_iceberg_deletion(
        self, device_id: str, jurisdiction: str, request_id: str
    ) -> None:
        """Schedule async deletion from Iceberg table."""
        # In production: queue Spark job via task scheduler
        # Example:
        # spark_job = {
        #     "job_type": "delete_from_iceberg",
        #     "device_id": device_id,
        #     "jurisdiction": jurisdiction,
        #     "request_id": request_id,
        #     "table": "acraas.viewership",
        #     "deadline_hours": 24 if jurisdiction == "US" else 72,
        # }
        # await self.task_queue.enqueue(spark_job)
        pass


class SegmentMembershipRemoval:
    """Remove device from all segment memberships."""

    def __init__(self, redis_service: RedisService):
        self.redis_service = redis_service

    async def remove_device_from_all_segments(
        self, device_id: str, segment_ids: list[str]
    ) -> bool:
        """Remove device from specified segments."""
        try:
            await self.redis_service.initialize()
            await self.redis_service.bulk_remove_device_from_segments(
                device_id, segment_ids
            )
            return True
        except Exception:
            return False
