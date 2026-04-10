"""Segment models and schemas."""
from typing import Optional, Literal
from datetime import datetime
from pydantic import BaseModel, Field


class SegmentRule(BaseModel):
    """Single rule in segment definition."""

    type: Literal[
        "watched_genre", "watched_network", "household_income", "dma", "daypart"
    ]
    value: str | int | list[str]
    operator: Optional[Literal[">=", "<=", "==", "in"]] = None
    min_hours_week: Optional[float] = None


class SegmentDefinition(BaseModel):
    """Segment definition with rules."""

    name: str = Field(min_length=3, max_length=100)
    rules: list[SegmentRule] = Field(min_length=1, max_length=20)
    logic: Literal["AND", "OR"] = "AND"
    lookback_days: int = Field(ge=1, le=90, default=30)
    minimum_cpm_floor: float = Field(ge=0.10, default=0.50)


class SegmentResponse(BaseModel):
    """Segment response model."""

    id: str
    name: str
    description: Optional[str]
    rules: list[SegmentRule]
    logic: str
    lookback_days: int
    minimum_cpm_floor: float
    status: str
    device_count: int
    household_count: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SegmentCreateResponse(BaseModel):
    """Response for segment creation."""

    segment_id: str
    status: str
    message: str


class SegmentSizeResponse(BaseModel):
    """Segment size response."""

    segment_id: str
    household_count: int
    device_count: int
    last_updated: datetime


class SegmentListResponse(BaseModel):
    """List of segments response."""

    total: int
    segments: list[SegmentResponse]
