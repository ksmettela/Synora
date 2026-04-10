import structlog
import time
from typing import Optional
from app import (
    app,
    matched_viewership_topic,
    device_sessions_table,
)
from models import ViewershipEvent, SessionStateEvent

logger = structlog.get_logger(__name__)

# Configuration
SESSION_TIMEOUT_SEC = 300  # 5 minutes
CHECK_INTERVAL_SEC = 30  # Check every 30 seconds


@app.timer(interval=CHECK_INTERVAL_SEC)
async def check_expired_sessions() -> None:
    """
    Periodically check for and emit expired sessions.

    Sessions expire after 5 minutes of inactivity.
    """
    current_time = int(time.time())

    try:
        # Get all active sessions
        sessions_to_remove = []

        for device_id, session_state in device_sessions_table.items():
            if session_state is None:
                continue

            session = session_state if isinstance(session_state, SessionStateEvent) else session_state.value()
            if session is None:
                continue

            # Check if session has expired
            time_since_last_match = current_time - session.last_match_utc
            if time_since_last_match > SESSION_TIMEOUT_SEC:
                # Emit final session
                await emit_completed_session(session)
                sessions_to_remove.append(device_id)

                logger.msg(
                    "Session expired",
                    device_id=device_id,
                    duration_sec=session.last_match_utc - session.watch_start_utc,
                )

        # Remove expired sessions
        for device_id in sessions_to_remove:
            try:
                del device_sessions_table[device_id]
            except Exception as e:
                logger.msg("Failed to delete session", device_id=device_id, error=str(e))

    except Exception as e:
        logger.msg("Error checking expired sessions", error=str(e), exc_info=True)


async def emit_completed_session(session: SessionStateEvent) -> None:
    """
    Emit a completed session as a viewership event.

    Calculates the session duration and publishes to matched.viewership.
    """
    try:
        duration_sec = session.last_match_utc - session.watch_start_utc

        # Only emit sessions with meaningful duration
        if duration_sec < 1:
            return

        viewership_event = ViewershipEvent(
            device_id=session.device_id,
            content_id=session.content_id,
            title=session.title,
            network=session.network,
            genre=session.genre,
            match_confidence=session.match_confidence,
            watch_start_utc=session.watch_start_utc,
            duration_sec=int(duration_sec),
            manufacturer=session.manufacturer,
            model=session.model,
        )

        await matched_viewership_topic.send(value=viewership_event)

        logger.msg(
            "Session completed and emitted",
            device_id=session.device_id,
            content_id=session.content_id,
            duration_sec=int(duration_sec),
        )

    except Exception as e:
        logger.msg(
            "Failed to emit completed session",
            device_id=session.device_id,
            error=str(e),
            exc_info=True,
        )


@app.agent(matched_viewership_topic)
async def aggregate_viewership(stream) -> None:
    """
    Consume matched viewership events for aggregation/logging.

    In production, these would be persisted to a data warehouse.
    """
    async for event in stream:
        try:
            logger.msg(
                "Viewership event received",
                device_id=event.device_id,
                content_id=event.content_id,
                title=event.title,
                duration_sec=event.duration_sec,
                match_confidence=event.match_confidence,
            )
        except Exception as e:
            logger.msg("Error processing viewership event", error=str(e), exc_info=True)
