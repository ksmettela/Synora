import aiohttp
import asyncio
import structlog
from typing import Optional, Dict, Any
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    RetryError,
)
import time

logger = structlog.get_logger(__name__)


class CircuitBreakerState:
    """Tracks circuit breaker state"""
    def __init__(self):
        self.consecutive_failures = 0
        self.is_open = False
        self.last_failure_time = 0
        self.failure_threshold = 5
        self.recovery_timeout = 30  # seconds


class FingerprintClient:
    """HTTP client for fingerprint-indexer service with resilience patterns"""

    def __init__(self, base_url: str = "http://fingerprint-indexer:8080"):
        self.base_url = base_url
        self.session: Optional[aiohttp.ClientSession] = None
        self.circuit_breaker = CircuitBreakerState()
        self.connector = None

    async def init(self) -> None:
        """Initialize the HTTP session with keep-alive"""
        if self.session is None:
            self.connector = aiohttp.TCPConnector(
                limit=100,
                limit_per_host=10,
                ttl_dns_cache=300,
                keepalive_timeout=30,
            )
            self.session = aiohttp.ClientSession(
                connector=self.connector,
                timeout=aiohttp.ClientTimeout(total=30, connect=10, sock_read=10),
            )
            logger.msg("FingerprintClient session initialized", url=self.base_url)

    async def close(self) -> None:
        """Close the HTTP session"""
        if self.session:
            await self.session.close()
            logger.msg("FingerprintClient session closed")

    def _check_circuit_breaker(self) -> None:
        """Check if circuit breaker should recover"""
        if self.circuit_breaker.is_open:
            current_time = time.time()
            elapsed = current_time - self.circuit_breaker.last_failure_time
            if elapsed >= self.circuit_breaker.recovery_timeout:
                self.circuit_breaker.is_open = False
                self.circuit_breaker.consecutive_failures = 0
                logger.msg("Circuit breaker recovered")

    def _record_success(self) -> None:
        """Record successful request"""
        self.circuit_breaker.consecutive_failures = 0
        if self.circuit_breaker.is_open:
            self.circuit_breaker.is_open = False
            logger.msg("Circuit breaker closed")

    def _record_failure(self) -> None:
        """Record failed request"""
        self.circuit_breaker.consecutive_failures += 1
        self.circuit_breaker.last_failure_time = time.time()

        if self.circuit_breaker.consecutive_failures >= self.circuit_breaker.failure_threshold:
            self.circuit_breaker.is_open = True
            logger.msg(
                "Circuit breaker opened after consecutive failures",
                failures=self.circuit_breaker.consecutive_failures,
            )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
    )
    async def _make_request(
        self, method: str, endpoint: str, **kwargs
    ) -> Dict[str, Any]:
        """Make HTTP request with retry logic"""
        if self.session is None:
            raise RuntimeError("Client not initialized. Call init() first.")

        self._check_circuit_breaker()

        if self.circuit_breaker.is_open:
            raise Exception("Circuit breaker is open")

        url = f"{self.base_url}{endpoint}"

        try:
            async with self.session.request(method, url, **kwargs) as response:
                if response.status >= 500:
                    self._record_failure()
                    raise aiohttp.ClientError(f"Server error: {response.status}")

                if response.status >= 400 and response.status < 500:
                    # Don't count 4xx errors against circuit breaker
                    data = await response.json()
                    return data

                data = await response.json()
                self._record_success()
                return data

        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            self._record_failure()
            raise

    async def lookup_fingerprint(
        self, fingerprint_hash: str, hamming_tolerance: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Lookup a fingerprint using hamming distance tolerance.

        Args:
            fingerprint_hash: 256-bit fingerprint as hex string
            hamming_tolerance: Max hamming distance (optional)

        Returns:
            Dictionary with match result or None if no match
        """
        try:
            payload = {
                "fingerprint_hash": fingerprint_hash,
            }
            if hamming_tolerance is not None:
                payload["hamming_tolerance"] = hamming_tolerance

            result = await self._make_request(
                "POST",
                "/v1/fingerprints/lookup",
                json=payload,
            )

            if result.get("matched"):
                return result.get("fingerprint")

            return None

        except Exception as e:
            logger.msg(
                "Fingerprint lookup failed",
                fingerprint=fingerprint_hash,
                error=str(e),
                exc_info=True,
            )
            return None

    async def index_fingerprint(self, fingerprint_data: Dict[str, Any]) -> bool:
        """
        Index a new fingerprint.

        Args:
            fingerprint_data: Fingerprint record with all required fields

        Returns:
            True if successful, False otherwise
        """
        try:
            result = await self._make_request(
                "POST",
                "/v1/fingerprints/index",
                json=fingerprint_data,
            )

            return result.get("success", False)

        except Exception as e:
            logger.msg(
                "Fingerprint indexing failed",
                fingerprint=fingerprint_data.get("fingerprint_hash"),
                error=str(e),
                exc_info=True,
            )
            return False

    async def get_stats(self) -> Optional[Dict[str, Any]]:
        """Get fingerprint statistics"""
        try:
            return await self._make_request("GET", "/v1/fingerprints/stats")
        except Exception as e:
            logger.msg("Failed to get stats", error=str(e))
            return None

    async def health_check(self) -> bool:
        """Check if fingerprint service is healthy"""
        try:
            result = await self._make_request("GET", "/health")
            return result.get("status") == "ok"
        except Exception as e:
            logger.msg("Health check failed", error=str(e))
            return False
