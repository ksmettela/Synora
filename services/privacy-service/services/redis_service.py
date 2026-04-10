"""Redis service for device operations in privacy service."""
from typing import Optional, Set
from redis.asyncio import Redis, from_url


class RedisService:
    """Redis operations for privacy management."""

    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        self.redis: Optional[Redis] = None

    async def initialize(self):
        """Initialize Redis connection."""
        self.redis = await from_url(self.redis_url, decode_responses=True)

    async def close(self):
        """Close Redis connection."""
        if self.redis:
            await self.redis.close()

    async def clear_device_segments(self, device_id: str) -> bool:
        """Remove all segment data for device (for opt-out)."""
        try:
            await self.redis.delete(f"device_segments:{device_id}")
            return True
        except Exception:
            return False

    async def bulk_remove_device_from_segments(
        self, device_id: str, segment_ids: list[str]
    ) -> bool:
        """Remove device from multiple segments."""
        try:
            for segment_id in segment_ids:
                await self.redis.srem(f"segment:{segment_id}", device_id)
            return True
        except Exception:
            return False

    async def get_device_segments(self, device_id: str) -> list[str]:
        """Get segments for device."""
        try:
            import json

            segments_json = await self.redis.hget(f"device_segments:{device_id}", "segments")
            if segments_json:
                return json.loads(segments_json)
            return []
        except Exception:
            return []

    async def remove_device_from_household_ip(self, ip_subnet: str, device_id: str) -> bool:
        """Remove device from IP household mapping."""
        try:
            await self.redis.srem(f"ip_household:{ip_subnet}", device_id)
            return True
        except Exception:
            return False
