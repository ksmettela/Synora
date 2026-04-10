"""Privacy database models."""
from datetime import datetime
from sqlalchemy import (
    Column,
    String,
    Integer,
    Boolean,
    Text,
    DateTime,
    Index,
    JSON,
)
from sqlalchemy.orm import declarative_base
from sqlalchemy.dialects.postgresql import JSONB, ARRAY

Base = declarative_base()


class ConsentRecord(Base):
    """Consent record for device."""

    __tablename__ = "consent_records"
    __table_args__ = (
        Index("ix_consent_records_device_id", "device_id"),
        Index("ix_consent_records_jurisdiction", "jurisdiction"),
        Index("ix_consent_records_timestamp", "consent_timestamp"),
    )

    device_id = Column(String, primary_key=True)
    opted_in = Column(Boolean, nullable=False, default=True)
    consent_timestamp = Column(DateTime(timezone=True), nullable=False)
    consent_version = Column(String)
    ip_at_consent = Column(String)  # /24 prefix only for privacy
    jurisdiction = Column(String, nullable=False)  # US, EU, CA
    tcf_string = Column(Text)  # IAB TCF 2.2 consent string
    purposes = Column(ARRAY(String))  # GDPR purposes consented
    vendors = Column(ARRAY(String))  # GDPR vendors consented
    special_features = Column(ARRAY(String))  # GDPR special features
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class OptOutRequest(Base):
    """Right to be forgotten / CCPA opt-out request."""

    __tablename__ = "opt_out_requests"
    __table_args__ = (
        Index("ix_opt_out_requests_device_id", "device_id"),
        Index("ix_opt_out_requests_status", "status"),
        Index("ix_opt_out_requests_requested_at", "requested_at"),
    )

    id = Column(String, primary_key=True)
    device_id = Column(String, nullable=False)
    jurisdiction = Column(String, nullable=False)  # US, EU, CA
    request_type = Column(String, nullable=False)  # opt_out, erasure, portability
    status = Column(String, nullable=False, default="pending")  # pending, in_progress, completed, failed
    requested_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    completion_deadline = Column(DateTime(timezone=True), nullable=False)
    completed_at = Column(DateTime(timezone=True))
    error_message = Column(Text)


class DataExportJob(Base):
    """GDPR data subject access request (DSAR) job."""

    __tablename__ = "data_export_jobs"
    __table_args__ = (
        Index("ix_data_export_jobs_device_id", "device_id"),
        Index("ix_data_export_jobs_status", "status"),
        Index("ix_data_export_jobs_requested_at", "requested_at"),
    )

    id = Column(String, primary_key=True)
    device_id = Column(String, nullable=False)
    requested_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    status = Column(String, nullable=False, default="pending")  # pending, processing, completed, failed
    export_url = Column(String)  # S3 pre-signed URL to ZIP file
    expiry = Column(DateTime(timezone=True))  # URL expiry
    error_message = Column(Text)
    completed_at = Column(DateTime(timezone=True))


class AuditLogEvent(Base):
    """Immutable audit log for privacy operations."""

    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_logs_device_id_hash", "device_id_hash"),
        Index("ix_audit_logs_action", "action"),
        Index("ix_audit_logs_timestamp", "timestamp"),
    )

    id = Column(String, primary_key=True)
    device_id_hash = Column(String, nullable=False)  # SHA256 hash for privacy
    action = Column(String, nullable=False)  # consent_recorded, opt_out, data_export, erasure
    jurisdiction = Column(String, nullable=False)
    operator_id = Column(String)  # Who triggered action
    metadata = Column(JSONB)  # Additional context
    timestamp = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    s3_path = Column(String)  # Path in audit bucket


class DatabaseManager:
    """Manages database connections and sessions."""

    def __init__(self, database_url: str):
        self.database_url = database_url
        self.engine = None
        self.async_session = None

    async def initialize(self):
        """Initialize async engine and session factory."""
        from sqlalchemy.ext.asyncio import (
            create_async_engine,
            async_sessionmaker,
            AsyncSession,
        )

        self.engine = create_async_engine(
            self.database_url,
            echo=False,
            pool_size=20,
            max_overflow=10,
            pool_pre_ping=True,
        )
        self.async_session = async_sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )

    async def close(self):
        """Close database connections."""
        if self.engine:
            await self.engine.dispose()

    async def create_tables(self):
        """Create all tables."""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    def get_session(self):
        """Get async database session."""
        return self.async_session()
