"""Rate limiting middleware."""
import time
from fastapi import Request, HTTPException, status
from redis.asyncio import Redis


class RateLimitMiddleware:
    """Per-client rate limiting middleware."""

    def __init__(self, redis: Redis, requests_per_minute: int = 1000):
        self.redis = redis
        self.requests_per_minute = requests_per_minute
        self.window_seconds = 60

    async def __call__(self, request: Request, call_next):
        """Apply rate limiting."""
        # Extract client ID from token or IP
        client_id = self._extract_client_id(request)

        # Check rate limit
        key = f"ratelimit:{client_id}"
        current = await self.redis.incr(key)

        if current == 1:
            # First request in window, set expiry
            await self.redis.expire(key, self.window_seconds)

        if current > self.requests_per_minute:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded",
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(self.requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(
            self.requests_per_minute - current
        )
        return response

    def _extract_client_id(self, request: Request) -> str:
        """Extract client ID from authorization header or IP."""
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            # Would decode JWT to get client_id
            return "client_from_token"

        # Fall back to IP address
        return request.client.host if request.client else "unknown"
