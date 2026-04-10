from dataclasses import dataclass
from typing import Optional
import faust


class FingerprintEvent(faust.Record):
    """Raw fingerprint event from device"""
    device_id: str
    fingerprint_hash: str
    timestamp_utc: int
    manufacturer: str
    model: str
    ip_address: str


class ViewershipEvent(faust.Record):
    """Matched viewership event - published to matched.viewership topic"""
    device_id: str
    content_id: str
    title: str
    network: str
    genre: str
    match_confidence: float
    watch_start_utc: int
    duration_sec: int
    manufacturer: str
    model: str


class UnmatchedEvent(faust.Record):
    """Unmatched fingerprint - published to unmatched.fingerprints topic"""
    device_id: str
    fingerprint_hash: str
    timestamp_utc: int
    manufacturer: str
    model: str
    ip_address: str


class SessionStateEvent(faust.Record):
    """Internal session state tracking"""
    device_id: str
    content_id: str
    title: str
    network: str
    genre: str
    match_confidence: float
    watch_start_utc: int
    last_match_utc: int
    manufacturer: str
    model: str
    ip_address: str
