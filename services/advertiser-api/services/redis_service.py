"""Redis service for device and segment operations."""
import json
from typing import Optional, Set
from redis.asyncio import Redis, from_url


class RedisService:
    """Redis operations for segments and device mapping."""

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

    async def set_device_segments(
        self, device_id: str, segment_ids: list[str], ttl: int = 86400
    ) -> bool:
        """Store device segment membership."""
        try:
            segments_json = json.dumps(segment_ids)
            await self.redis.hset(
                f"device_segments:{device_id}",
                "segments",
                segments_json,
            )
            await self.redis.expire(f"device_segments:{device_id}", ttl)
            return True
        except Exception:
            return False

    async def get_device_segments(self, device_id: str) -> list[str]:
        """Get segments for device."""
        try:
            segments_json = await self.redis.hget(f"device_segments:{device_id}", "segments")
            if segments_json:
                return json.loads(segments_json)
            return []
        except Exception:
            return []

    async def add_device_to_segment(self, segment_id: str, device_id: str) -> bool:
        """Add device to segment set."""
        try:
            await self.redis.sadd(f"segment:{segment_id}", device_id)
            return True
        except Exception:
            return False

    async def get_segment_devices(self, segment_id: str) -> Set[str]:
        """Get all devices in segment."""
        try:
            return await self.redis.smembers(f"segment:{segment_id}")
        except Exception:
            return set()

    async def get_segment_size(self, segment_id: str) -> int:
        """Get segment size (device count)."""
        try:
            return await self.redis.scard(f"segment:{segment_id}")
        except Exception:
            return 0

    async def get_household_by_ip(self, ip_subnet: str) -> Set[str]:
        """Lookup households by IP /24 subnet."""
        try:
            return await self.redis.smembers(f"ip_household:{ip_subnet}")
        except Exception:
            return set()

    async def set_household_by_ip(
        self, ip_subnet: str, household_ids: Set[str], ttl: int = 604800
    ) -> bool:
        """Store household mapping for IP subnet."""
        try:
            if household_ids:
                await self.redis.sadd(f"ip_household:{ip_subnet}", *household_ids)
                await self.redis.expire(f"ip_household:{ip_subnet}", ttl)
            return True
        except Exception:
            return False

    async def get_segment_intersection_count(
        self, segment_ids: list[str]
    ) -> int:
        """Count devices in intersection of multiple segments (SINTERCARD)."""
        try:
            if not segment_ids or len(segment_ids) < 2:
                if segment_ids:
                    return await self.get_segment_size(segment_ids[0])
                return 0

            keys = [f"segment:{s_id}" for s_id in segment_ids]
            # Use SINTERCARD for cardinality without fetching all members
            result = await self.redis.execute_command("SINTERCARD", len(keys), *keys)
            return result
        except Exception:
            return 0

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
