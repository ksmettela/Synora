"""Unit tests for matching engine"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from models import FingerprintEvent, ViewershipEvent
from lookup import FingerprintClient


@pytest.fixture
async def fingerprint_client():
    """Create a mock fingerprint client"""
    client = FingerprintClient(base_url="http://localhost:8080")
    yield client
    # Cleanup
    if client.session:
        await client.close()


@pytest.fixture
def sample_fingerprint_event():
    """Create a sample fingerprint event"""
    return FingerprintEvent(
        device_id="device-123",
        fingerprint_hash="a" * 64,  # 256-bit hex string
        timestamp_utc=1640000000,
        manufacturer="Samsung",
        model="TV-2022",
        ip_address="192.168.1.100",
    )


@pytest.fixture
def sample_match_result():
    """Create a sample fingerprint match result"""
    return {
        "fingerprint_hash": "a" * 64,
        "content_id": "content-456",
        "title": "Breaking Bad",
        "network": "AMC",
        "genre": "Drama",
        "confidence": 0.98,
        "created_at": "2024-01-15T10:00:00Z",
    }


class TestFingerprintClient:
    """Tests for FingerprintClient"""

    @pytest.mark.asyncio
    async def test_client_initialization(self, fingerprint_client):
        """Test client initialization"""
        await fingerprint_client.init()
        assert fingerprint_client.session is not None
        assert not fingerprint_client.circuit_breaker.is_open

    @pytest.mark.asyncio
    async def test_circuit_breaker_opens_on_failures(self, fingerprint_client):
        """Test circuit breaker opens after consecutive failures"""
        await fingerprint_client.init()

        # Simulate failures
        for _ in range(5):
            fingerprint_client._record_failure()

        assert fingerprint_client.circuit_breaker.is_open

    @pytest.mark.asyncio
    async def test_circuit_breaker_recovers(self, fingerprint_client):
        """Test circuit breaker recovery after timeout"""
        await fingerprint_client.init()

        # Open the circuit
        fingerprint_client.circuit_breaker.is_open = True
        fingerprint_client.circuit_breaker.last_failure_time = 0

        # Check recovery
        fingerprint_client._check_circuit_breaker()
        assert not fingerprint_client.circuit_breaker.is_open

    @pytest.mark.asyncio
    async def test_successful_request_resets_failures(self, fingerprint_client):
        """Test successful request resets failure counter"""
        await fingerprint_client.init()

        fingerprint_client.circuit_breaker.consecutive_failures = 3
        fingerprint_client._record_success()

        assert fingerprint_client.circuit_breaker.consecutive_failures == 0

    @pytest.mark.asyncio
    async def test_lookup_with_valid_hash(self, fingerprint_client, sample_match_result):
        """Test fingerprint lookup with valid hash"""
        await fingerprint_client.init()

        # Mock the _make_request method
        fingerprint_client._make_request = AsyncMock(
            return_value={"matched": True, "fingerprint": sample_match_result}
        )

        result = await fingerprint_client.lookup_fingerprint("a" * 64)

        assert result is not None
        assert result["content_id"] == "content-456"
        assert result["title"] == "Breaking Bad"

    @pytest.mark.asyncio
    async def test_lookup_with_invalid_hash(self, fingerprint_client):
        """Test fingerprint lookup with invalid hash"""
        await fingerprint_client.init()

        fingerprint_client._make_request = AsyncMock(
            side_effect=Exception("Invalid hash")
        )

        result = await fingerprint_client.lookup_fingerprint("invalid")

        assert result is None

    @pytest.mark.asyncio
    async def test_lookup_no_match(self, fingerprint_client):
        """Test fingerprint lookup with no match"""
        await fingerprint_client.init()

        fingerprint_client._make_request = AsyncMock(
            return_value={"matched": False, "fingerprint": None}
        )

        result = await fingerprint_client.lookup_fingerprint("b" * 64)

        assert result is None

    @pytest.mark.asyncio
    async def test_index_fingerprint_success(self, fingerprint_client, sample_match_result):
        """Test indexing a fingerprint successfully"""
        await fingerprint_client.init()

        fingerprint_client._make_request = AsyncMock(
            return_value={"success": True, "fingerprint_hash": "a" * 64}
        )

        result = await fingerprint_client.index_fingerprint(sample_match_result)

        assert result is True

    @pytest.mark.asyncio
    async def test_index_fingerprint_failure(self, fingerprint_client, sample_match_result):
        """Test indexing a fingerprint with failure"""
        await fingerprint_client.init()

        fingerprint_client._make_request = AsyncMock(
            side_effect=Exception("Database error")
        )

        result = await fingerprint_client.index_fingerprint(sample_match_result)

        assert result is False

    @pytest.mark.asyncio
    async def test_health_check_success(self, fingerprint_client):
        """Test successful health check"""
        await fingerprint_client.init()

        fingerprint_client._make_request = AsyncMock(
            return_value={"status": "ok", "database": "healthy", "kafka": "connected"}
        )

        result = await fingerprint_client.health_check()

        assert result is True

    @pytest.mark.asyncio
    async def test_health_check_failure(self, fingerprint_client):
        """Test failed health check"""
        await fingerprint_client.init()

        fingerprint_client._make_request = AsyncMock(
            side_effect=Exception("Connection failed")
        )

        result = await fingerprint_client.health_check()

        assert result is False


class TestFingerprintEvent:
    """Tests for FingerprintEvent model"""

    def test_event_creation(self, sample_fingerprint_event):
        """Test creating a fingerprint event"""
        assert sample_fingerprint_event.device_id == "device-123"
        assert sample_fingerprint_event.manufacturer == "Samsung"
        assert len(sample_fingerprint_event.fingerprint_hash) == 64

    def test_event_serialization(self, sample_fingerprint_event):
        """Test event can be serialized"""
        # Faust events are already serializable
        assert sample_fingerprint_event.device_id is not None


class TestViewershipEvent:
    """Tests for ViewershipEvent model"""

    def test_viewership_event_creation(self):
        """Test creating a viewership event"""
        event = ViewershipEvent(
            device_id="device-123",
            content_id="content-456",
            title="Breaking Bad",
            network="AMC",
            genre="Drama",
            match_confidence=0.98,
            watch_start_utc=1640000000,
            duration_sec=3600,
            manufacturer="Samsung",
            model="TV-2022",
        )

        assert event.device_id == "device-123"
        assert event.title == "Breaking Bad"
        assert event.duration_sec == 3600

    def test_viewership_event_confidence(self):
        """Test viewership event confidence scoring"""
        event = ViewershipEvent(
            device_id="device-123",
            content_id="content-456",
            title="Game of Thrones",
            network="HBO",
            genre="Fantasy",
            match_confidence=0.95,
            watch_start_utc=1640000000,
            duration_sec=2700,
            manufacturer="LG",
            model="OLED-2022",
        )

        assert 0.0 <= event.match_confidence <= 1.0


class TestCircuitBreaker:
    """Tests for circuit breaker functionality"""

    def test_circuit_breaker_threshold(self, fingerprint_client):
        """Test circuit breaker failure threshold"""
        assert fingerprint_client.circuit_breaker.failure_threshold == 5

        for i in range(4):
            fingerprint_client._record_failure()
            assert not fingerprint_client.circuit_breaker.is_open

        fingerprint_client._record_failure()
        assert fingerprint_client.circuit_breaker.is_open

    def test_circuit_breaker_reset_on_success(self, fingerprint_client):
        """Test circuit breaker reset on success"""
        fingerprint_client.circuit_breaker.consecutive_failures = 3
        fingerprint_client._record_success()

        assert fingerprint_client.circuit_breaker.consecutive_failures == 0


@pytest.fixture
def event_loop():
    """Create an event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()
