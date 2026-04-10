"""OpenRTB protocol models."""
from typing import Optional
from pydantic import BaseModel, Field


class Device(BaseModel):
    """Device information from OpenRTB."""

    id: Optional[str] = None
    ip: Optional[str] = None
    ipv6: Optional[str] = None
    ua: Optional[str] = None
    make: Optional[str] = None
    model: Optional[str] = None
    os: Optional[str] = None
    osv: Optional[str] = None
    ifa: Optional[str] = None


class OpenRTBLookupRequest(BaseModel):
    """RTB device lookup request."""

    device_id: Optional[str] = None
    ip_address: Optional[str] = None
    device: Optional[Device] = None


class SegmentMatch(BaseModel):
    """Matched segment for device."""

    segment_id: str
    confidence: float = Field(ge=0.0, le=1.0)
    source: str  # "device_hash", "ip_household", "inference"


class OpenRTBLookupResponse(BaseModel):
    """RTB device lookup response."""

    device_id: str
    matched_segments: list[SegmentMatch]
    lookup_time_ms: float
    cache_hit: bool


class ActivationRequest(BaseModel):
    """Segment activation request."""

    segment_id: str
    cpm_floor: float = Field(ge=0.10)
    daily_budget: Optional[float] = None


class ActivationResponse(BaseModel):
    """Segment activation response."""

    activation_id: str
    segment_id: str
    status: str
    activated_at: str


class ReachEstimate(BaseModel):
    """Segment reach estimate."""

    segment_id: str
    household_count: int
    device_count: int
    estimated_impressions_daily: int
    estimated_reach_percentage: float
