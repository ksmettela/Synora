import os
import logging
from typing import Dict, Optional
import faust
import structlog
from dotenv import load_dotenv

load_dotenv()

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)

# Faust App Configuration
KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "kafka:9092")
FINGERPRINT_SERVICE_URL = os.getenv("FINGERPRINT_SERVICE_URL", "http://fingerprint-indexer:8080")

app = faust.App(
    "matching-engine",
    broker=f"kafka://{KAFKA_BOOTSTRAP}",
    version=1,
    autodiscover=True,
    value_serializer="json",
    logging_config={
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": "[%(asctime)s] %(levelname)s - %(name)s - %(message)s"
            },
        },
        "handlers": {
            "default": {
                "level": "DEBUG",
                "class": "logging.StreamHandler",
                "formatter": "default",
                "stream": "ext://sys.stdout",
            },
        },
        "loggers": {
            "": {"handlers": ["default"], "level": "DEBUG", "propagate": True},
        },
    },
)

logger.msg("Faust app initialized", bootstrap=KAFKA_BOOTSTRAP)


class FingerprintEvent(faust.Record):
    """Raw fingerprint from device"""
    device_id: str
    fingerprint_hash: str
    timestamp_utc: int
    manufacturer: str
    model: str
    ip_address: str


class ViewershipEvent(faust.Record):
    """Matched viewership event"""
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


class DeviceSession(faust.Record):
    """Device watch session tracking"""
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


# Topics
raw_fingerprints_topic = app.topic("raw.fingerprints", value_type=FingerprintEvent)
matched_viewership_topic = app.topic("matched.viewership", value_type=ViewershipEvent)
unmatched_fingerprints_topic = app.topic("unmatched.fingerprints", value_type=FingerprintEvent)

# Faust Tables for state
device_sessions_table = app.Table(
    "device_sessions",
    default=DeviceSession,
    key_type=str,
    value_type=DeviceSession,
    ttl=300,  # 5 minute TTL
).hopping(30, expires=300)

fingerprint_cache = app.Table(
    "fingerprint_cache",
    key_type=str,
    value_type=dict,
    ttl=3600,  # 1 hour cache
)

logger.msg("Topics and tables configured")


@app.task()
async def on_started() -> None:
    """Called when app starts"""
    logger.msg("Matching engine started")


@app.task()
async def on_rebalance() -> None:
    """Called when partition rebalance occurs"""
    logger.msg("Partition rebalance occurred")
