"""Consent models and schemas."""
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field


class ConsentRecord(BaseModel):
    """Consent record for device."""

    device_id: str = Field(min_length=1)
    opted_in: bool
    consent_timestamp: datetime
    consent_version: Optional[str] = None
    ip_at_consent: Optional[str] = None  # /24 prefix only
    jurisdiction: str = Field(pattern="^(US|EU|CA)$")
    tcf_string: Optional[str] = None


class ConsentResponse(BaseModel):
    """Response after recording consent."""

    device_id: str
    status: str
    message: str


class ConsentStatus(BaseModel):
    """Current consent status for device."""

    device_id: str
    opted_in: bool
    last_updated: datetime
    jurisdiction: str


class OptOutRequest(BaseModel):
    """Right to be forgotten request."""

    device_id: str
    jurisdiction: str = Field(pattern="^(US|EU|CA)$")
    reason: Optional[str] = None


class OptOutResponse(BaseModel):
    """Response to opt-out request."""

    request_id: str
    device_id: str
    status: str
    deadline: datetime
    message: str


class DataExportRequest(BaseModel):
    """GDPR DSAR request."""

    device_id: str
    format: str = Field(default="json", pattern="^(json|csv|xml)$")


class DataExportResponse(BaseModel):
    """GDPR DSAR export response."""

    job_id: str
    device_id: str
    status: str
    export_url: Optional[str] = None
    expiry: Optional[datetime] = None
    message: str


class EraseRequest(BaseModel):
    """GDPR right to erasure request."""

    device_id: str
    jurisdiction: str = Field(pattern="^(US|EU|CA)$")


class EraseResponse(BaseModel):
    """Response to erasure request."""

    request_id: str
    device_id: str
    status: str
    deadline: datetime
    message: str


class TCFConsentRequest(BaseModel):
    """IAB TCF 2.2 consent request."""

    device_id: str
    tcf_string: str  # Base64-encoded TCF string
    ip_address: Optional[str] = None


class TCFResponse(BaseModel):
    """Response to TCF consent request."""

    device_id: str
    status: str
    purposes: list[str]
    vendors: list[str]
    special_features: list[str]
    message: str
