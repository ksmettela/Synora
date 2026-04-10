"""Immutable audit log service for privacy operations."""
import hashlib
import json
from datetime import datetime
from typing import Optional
from io import BytesIO
import uuid


class AuditLogger:
    """Write immutable audit logs to S3."""

    def __init__(self, s3_client, bucket: str = "acraas-audit-log"):
        self.s3_client = s3_client
        self.bucket = bucket

    async def log_action(
        self,
        device_id_hash: str,
        action: str,
        jurisdiction: str,
        operator_id: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> bool:
        """
        Log privacy action to immutable audit trail on S3.

        Path: /{year}/{month}/{day}/{timestamp}-{action}-{uuid}.json
        """
        try:
            now = datetime.utcnow()
            timestamp = now.isoformat()

            # Build S3 path
            year = now.strftime("%Y")
            month = now.strftime("%m")
            day = now.strftime("%d")
            log_id = str(uuid.uuid4())
            s3_key = f"{year}/{month}/{day}/{timestamp}-{action}-{log_id}.json"

            # Build log entry
            log_entry = {
                "log_id": log_id,
                "timestamp": timestamp,
                "action": action,
                "device_id_hash": device_id_hash,
                "jurisdiction": jurisdiction,
                "operator_id": operator_id,
                "metadata": metadata or {},
            }

            # Write to S3
            log_json = json.dumps(log_entry, indent=2)
            await self.s3_client.put_object(
                Bucket=self.bucket,
                Key=s3_key,
                Body=log_json.encode("utf-8"),
                ContentType="application/json",
                ServerSideEncryption="AES256",
            )

            return True

        except Exception as e:
            # In production: log to CloudWatch
            print(f"Failed to write audit log: {str(e)}")
            return False

    async def get_audit_logs(
        self, device_id_hash: str, days: int = 90
    ) -> list[dict]:
        """Retrieve audit logs for device (for compliance verification)."""
        try:
            logs = []
            paginator = self.s3_client.get_paginator("list_objects_v2")

            pages = paginator.paginate(Bucket=self.bucket, Prefix="")

            for page in pages:
                if "Contents" not in page:
                    continue

                for obj in page["Contents"]:
                    # Filter by device hash in metadata
                    response = await self.s3_client.get_object(
                        Bucket=self.bucket, Key=obj["Key"]
                    )
                    body = await response["Body"].read()
                    log_entry = json.loads(body)

                    if log_entry.get("device_id_hash") == device_id_hash:
                        logs.append(log_entry)

            return logs

        except Exception:
            return []
