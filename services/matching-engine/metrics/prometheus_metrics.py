"""Prometheus metrics for Synora matching engine"""

from prometheus_client import Counter, Histogram, Gauge, Registry
import structlog

logger = structlog.get_logger(__name__)

# Create registry
metrics_registry = Registry()

# Counter: Total matches found
matches_total = Counter(
    "acraas_matches_total",
    "Total successful fingerprint matches",
    labelnames=["network", "genre", "match_type"],
    registry=metrics_registry,
)

# Counter: Total unmatched fingerprints
unmatched_total = Counter(
    "acraas_unmatched_total",
    "Total unmatched fingerprints",
    labelnames=["manufacturer"],
    registry=metrics_registry,
)

# Histogram: Match latency in seconds
match_latency_seconds = Histogram(
    "acraas_match_latency_seconds",
    "Time taken to match a fingerprint",
    labelnames=["source"],
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 5.0],
    registry=metrics_registry,
)

# Gauge: Active sessions
active_sessions = Gauge(
    "acraas_active_sessions",
    "Number of active device sessions",
    labelnames=["network"],
    registry=metrics_registry,
)

# Counter: Cache hits/misses
cache_hits = Counter(
    "acraas_cache_hits_total",
    "Total fingerprint cache hits",
    registry=metrics_registry,
)

cache_misses = Counter(
    "acraas_cache_misses_total",
    "Total fingerprint cache misses",
    registry=metrics_registry,
)

# Counter: API errors from fingerprint service
api_errors = Counter(
    "acraas_fingerprint_api_errors_total",
    "Total errors calling fingerprint-indexer API",
    labelnames=["error_type"],
    registry=metrics_registry,
)

# Gauge: Circuit breaker status
circuit_breaker_status = Gauge(
    "acraas_circuit_breaker_open",
    "Circuit breaker status (1=open, 0=closed)",
    labelnames=["service"],
    registry=metrics_registry,
)

# Counter: Processed messages
messages_processed = Counter(
    "acraas_messages_processed_total",
    "Total messages processed",
    labelnames=["topic", "status"],
    registry=metrics_registry,
)


def record_match(network: str, genre: str, match_type: str = "exact") -> None:
    """Record a successful match"""
    matches_total.labels(network=network, genre=genre, match_type=match_type).inc()


def record_unmatched(manufacturer: str) -> None:
    """Record an unmatched fingerprint"""
    unmatched_total.labels(manufacturer=manufacturer).inc()


def record_match_latency(latency_sec: float, source: str = "cache") -> None:
    """Record match latency"""
    match_latency_seconds.labels(source=source).observe(latency_sec)


def set_active_sessions(count: int, network: str) -> None:
    """Set active session count"""
    active_sessions.labels(network=network).set(count)


def record_cache_hit() -> None:
    """Record a cache hit"""
    cache_hits.inc()


def record_cache_miss() -> None:
    """Record a cache miss"""
    cache_misses.inc()


def record_api_error(error_type: str) -> None:
    """Record an API error"""
    api_errors.labels(error_type=error_type).inc()


def set_circuit_breaker_status(is_open: bool, service: str = "fingerprint-indexer") -> None:
    """Set circuit breaker status"""
    circuit_breaker_status.labels(service=service).set(1 if is_open else 0)


def record_message_processed(topic: str, status: str = "success") -> None:
    """Record a processed message"""
    messages_processed.labels(topic=topic, status=status).inc()


logger.msg("Prometheus metrics initialized")
