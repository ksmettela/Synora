import structlog
import asyncio
import time
from typing import Optional, Dict, Any
from app import (
    app,
    raw_fingerprints_topic,
    matched_viewership_topic,
    unmatched_fingerprints_topic,
    fingerprint_cache,
    device_sessions_table,
)
from models import FingerprintEvent, ViewershipEvent, UnmatchedEvent, SessionStateEvent
from lookup import FingerprintClient

logger = structlog.get_logger(__name__)

# Initialize the fingerprint client
fingerprint_client: Optional[FingerprintClient] = None


@app.task()
async def init_fingerprint_client() -> None:
    """Initialize fingerprint client at app startup"""
    global fingerprint_client
    fingerprint_client = FingerprintClient()
    await fingerprint_client.init()
    logger.msg("Fingerprint client initialized")

    # Verify connectivity
    health = await fingerprint_client.health_check()
    if health:
        logger.msg("Fingerprint service is healthy")
    else:
        logger.msg("Warning: Fingerprint service health check failed")


@app.agent(raw_fingerprints_topic)
async def match_fingerprints(stream) -> None:
    """
    Core matching agent that processes raw fingerprints.

    Flow:
    1. Check in-memory cache for recent matches
    2. Call fingerprint-indexer HTTP API for hamming distance lookup
    3. On match: emit to matched.viewership
    4. On no match: emit to unmatched.fingerprints
    5. Update device session tracking
    """
    async for event in stream:
        try:
            await process_fingerprint(event)
        except Exception as e:
            logger.msg(
                "Error processing fingerprint",
                device_id=event.device_id,
                error=str(e),
                exc_info=True,
            )


async def process_fingerprint(event: FingerprintEvent) -> None:
    """Process a single fingerprint event"""
    device_id = event.device_id
    fingerprint_hash = event.fingerprint_hash

    start_time = time.time()

    # Step 1: Check cache
    cache_key = fingerprint_hash
    cached_match = None
    try:
        cached_data = fingerprint_cache[cache_key].value()
        if cached_data:
            cached_match = cached_data
            logger.msg(
                "Cache hit",
                device_id=device_id,
                fingerprint=fingerprint_hash[:16],
            )
    except Exception:
        pass

    # Step 2: Lookup with hamming distance tolerance
    match_result = None
    if cached_match:
        match_result = cached_match
    else:
        try:
            if fingerprint_client:
                match_result = await fingerprint_client.lookup_fingerprint(
                    fingerprint_hash,
                    hamming_tolerance=8,
                )
                if match_result:
                    # Cache the result
                    try:
                        fingerprint_cache[cache_key] = match_result
                    except Exception as e:
                        logger.msg("Cache write failed", error=str(e))
        except Exception as e:
            logger.msg(
                "Fingerprint lookup failed",
                device_id=device_id,
                error=str(e),
                exc_info=True,
            )

    lookup_time_ms = (time.time() - start_time) * 1000

    # Step 3: On match
    if match_result:
        await handle_match(event, match_result, lookup_time_ms)
    else:
        # Step 4: On no match
        await handle_no_match(event)

    # Step 5: Update session tracking
    await update_session(event, match_result)


async def handle_match(
    event: FingerprintEvent,
    match_result: Dict[str, Any],
    lookup_time_ms: float,
) -> None:
    """Handle a successful fingerprint match"""
    device_id = event.device_id

    # Compute confidence score (combination of fingerprint confidence and match)
    fingerprint_confidence = match_result.get("confidence", 0.95)
    match_confidence = min(fingerprint_confidence, 1.0)

    # Create viewership event
    viewership_event = ViewershipEvent(
        device_id=device_id,
        content_id=match_result.get("content_id", "unknown"),
        title=match_result.get("title", "Unknown"),
        network=match_result.get("network", "unknown"),
        genre=match_result.get("genre", "unknown"),
        match_confidence=match_confidence,
        watch_start_utc=event.timestamp_utc,
        duration_sec=0,  # Will be updated by session tracker
        manufacturer=event.manufacturer,
        model=event.model,
    )

    # Emit to matched topic
    await matched_viewership_topic.send(value=viewership_event)

    logger.msg(
        "Fingerprint matched",
        device_id=device_id,
        content_id=match_result.get("content_id"),
        title=match_result.get("title"),
        lookup_time_ms=lookup_time_ms,
    )


async def handle_no_match(event: FingerprintEvent) -> None:
    """Handle unmatched fingerprint"""
    unmatched_event = UnmatchedEvent(
        device_id=event.device_id,
        fingerprint_hash=event.fingerprint_hash,
        timestamp_utc=event.timestamp_utc,
        manufacturer=event.manufacturer,
        model=event.model,
        ip_address=event.ip_address,
    )

    # Emit to unmatched topic
    await unmatched_fingerprints_topic.send(value=unmatched_event)

    logger.msg(
        "No fingerprint match found",
        device_id=event.device_id,
    )


async def update_session(
    event: FingerprintEvent,
    match_result: Optional[Dict[str, Any]],
) -> None:
    """Update device watch session state"""
    device_id = event.device_id
    session_key = device_id

    try:
        if match_result:
            # Create or update session
            session = SessionStateEvent(
                device_id=device_id,
                content_id=match_result.get("content_id", "unknown"),
                title=match_result.get("title", "Unknown"),
                network=match_result.get("network", "unknown"),
                genre=match_result.get("genre", "unknown"),
                match_confidence=match_result.get("confidence", 0.95),
                watch_start_utc=event.timestamp_utc,
                last_match_utc=event.timestamp_utc,
                manufacturer=event.manufacturer,
                model=event.model,
                ip_address=event.ip_address,
            )
            device_sessions_table[session_key] = session
            logger.msg("Session updated", device_id=device_id)
        else:
            # Keep existing session if no match (will expire after TTL)
            try:
                existing = device_sessions_table[session_key].value()
                if existing:
                    # Update last_match time
                    existing.last_match_utc = event.timestamp_utc
                    device_sessions_table[session_key] = existing
            except Exception:
                pass

    except Exception as e:
        logger.msg(
            "Failed to update session",
            device_id=device_id,
            error=str(e),
            exc_info=True,
        )
