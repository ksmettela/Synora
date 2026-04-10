"""PostgreSQL database configuration and models."""
from datetime import datetime
from typing import Optional
from sqlalchemy import (
    Column,
    String,
    Integer,
    Float,
    Boolean,
    Text,
    DateTime,
    Index,
    JSON,
    select,
)
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    create_async_engine,
    async_sessionmaker,
)
from sqlalchemy.orm import declarative_base, Session
from sqlalchemy.dialects.postgresql import ARRAY, JSONB

Base = declarative_base()


class Segment(Base):
    """Segment definition and metadata."""

    __tablename__ = "segments"
    __table_args__ = (
        Index("ix_segments_status", "status"),
        Index("ix_segments_created_at", "created_at"),
    )

    id = Column(String, primary_key=True)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text)
    rules_json = Column(JSONB, nullable=False)
    logic = Column(String(3), nullable=False, default="AND")  # AND or OR
    lookback_days = Column(Integer, nullable=False, default=30)
    minimum_cpm_floor = Column(Float, nullable=False, default=0.50)
    status = Column(String(20), nullable=False, default="pending")  # pending, active, error
    device_count = Column(Integer, default=0)
    household_count = Column(Integer, default=0)
    error_message = Column(Text)
    created_by = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class OAuthClient(Base):
    """OAuth2 client credentials."""

    __tablename__ = "oauth_clients"
    __table_args__ = (Index("ix_oauth_clients_created_at", "created_at"),)

    client_id = Column(String, primary_key=True)
    client_secret_hash = Column(String, nullable=False)
    name = Column(String(100), nullable=False)
    scopes = Column(ARRAY(String), nullable=False, default=["segments:read"])
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class SegmentActivation(Base):
    """Record of segment activation for billing."""

    __tablename__ = "segment_activations"
    __table_args__ = (
        Index("ix_segment_activations_segment_id", "segment_id"),
        Index("ix_segment_activations_client_id", "client_id"),
        Index("ix_segment_activations_activated_at", "activated_at"),
    )

    id = Column(String, primary_key=True)
    segment_id = Column(String, nullable=False)
    client_id = Column(String, nullable=False)
    cpm_floor = Column(Float, nullable=False)
    device_count = Column(Integer, nullable=False)
    activated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)


class APIUsage(Base):
    """API usage tracking for rate limiting and analytics."""

    __tablename__ = "api_usage"
    __table_args__ = (
        Index("ix_api_usage_client_id", "client_id"),
        Index("ix_api_usage_timestamp", "timestamp"),
    )

    id = Column(String, primary_key=True)
    client_id = Column(String, nullable=False)
    endpoint = Column(String, nullable=False)
    method = Column(String(10), nullable=False)
    response_ms = Column(Integer, nullable=False)
    status_code = Column(Integer, nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)


class DatabaseManager:
    """Manages database connections and sessions."""

    def __init__(self, database_url: str):
        self.database_url = database_url
        self.engine = None
        self.async_session = None

    async def initialize(self):
        """Initialize async engine and session factory."""
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

    def get_session(self) -> AsyncSession:
        """Get async database session."""
        return self.async_session()
