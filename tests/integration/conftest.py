"""
Pytest configuration and shared fixtures for ACRaaS integration tests.
"""
import pytest
import httpx
import hashlib
import time
import random
import os
import json
from kafka import KafkaConsumer
import redis
from typing import Generator, Tuple

# Service URLs from environment variables
INGEST_BASE = os.getenv("INGEST_BASE_URL", "http://localhost:8080")
INDEXER_BASE = os.getenv("INDEXER_BASE_URL", "http://localhost:8082")
API_BASE = os.getenv("API_BASE_URL", "http://localhost:8084")
PRIVACY_BASE = os.getenv("PRIVACY_BASE_URL", "http://localhost:8085")
BILLING_BASE = os.getenv("BILLING_BASE_URL", "http://localhost:8086")
KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
TEST_API_KEY = os.getenv("TEST_API_KEY", "test-api-key-001")
TEST_CLIENT_ID = os.getenv("TEST_CLIENT_ID", "test-client-001")
TEST_CLIENT_SECRET = os.getenv("TEST_CLIENT_SECRET", "test-client-secret-001")


@pytest.fixture(scope="session")
def redis_client() -> redis.Redis:
    """
    Returns a connected Redis client.
    Skips test if Redis is unavailable.
    """
    try:
        client = redis.from_url(REDIS_URL, decode_responses=True, socket_connect_timeout=5)
        client.ping()
        yield client
        client.close()
    except (redis.ConnectionError, redis.TimeoutError) as e:
        pytest.skip(f"Redis unavailable at {REDIS_URL}: {e}")


@pytest.fixture
def kafka_consumer(request) -> Generator[KafkaConsumer, None, None]:
    """
    Factory fixture that returns a KafkaConsumer for a given topic.
    Skips test if Kafka is unavailable.
    Usage: consumer = kafka_consumer("topic_name")
    """
    def _consumer_factory(topic: str) -> KafkaConsumer:
        try:
            consumer = KafkaConsumer(
                topic,
                bootstrap_servers=KAFKA_BOOTSTRAP,
                auto_offset_reset='earliest',
                enable_auto_commit=True,
                group_id=f"test-group-{int(time.time() * 1000)}-{random.randint(1000, 9999)}",
                consumer_timeout_ms=15000,
                session_timeout_ms=30000,
            )
            return consumer
        except Exception as e:
            pytest.skip(f"Kafka unavailable at {KAFKA_BOOTSTRAP}: {e}")

    return _consumer_factory


@pytest.fixture
def auth_token() -> str:
    """
    POSTs to /v1/auth/token with test client credentials.
    Returns Bearer token string.
    """
    client = httpx.Client(base_url=API_BASE, timeout=10.0)
    try:
        response = client.post(
            "/v1/auth/token",
            json={
                "client_id": TEST_CLIENT_ID,
                "client_secret": TEST_CLIENT_SECRET,
                "grant_type": "client_credentials"
            }
        )
        assert response.status_code == 200, f"Failed to get auth token: {response.text}"
        token = response.json().get("access_token")
        assert token, "No access_token in response"
        return token
    finally:
        client.close()


@pytest.fixture
def test_device_id() -> str:
    """
    Returns SHA256(random_mac + manufacturer + model + salt) as hex string.
    Simulates a real device fingerprint ID.
    """
    random_mac = "".join([f"{random.randint(0, 255):02x}" for _ in range(6)])
    manufacturer = random.choice(["LG", "Vizio", "TCL", "Sony", "Hisense", "Samsung", "Panasonic"])
    model = f"MODEL-{random.randint(1000, 9999)}"
    salt = str(random.random())

    device_string = f"{random_mac}{manufacturer}{model}{salt}"
    return hashlib.sha256(device_string.encode()).hexdigest()


@pytest.fixture
def test_fingerprint() -> str:
    """
    Returns a random 64-char hex string representing a fingerprint hash.
    """
    return hashlib.sha256(str(random.random()).encode()).hexdigest()


@pytest.fixture
def reference_fingerprint(redis_client) -> Tuple[str, str, str, str, str]:
    """
    Indexes a known fingerprint in the indexer and returns
    (fingerprint_hash, content_id, title, network, genre).
    """
    fingerprint_hash = hashlib.sha256(b"reference-fingerprint-test-001").hexdigest()
    content_id = f"content-{int(time.time())}-{random.randint(10000, 99999)}"
    title = "Test Content Title"
    network = "NBC"
    genre = "Entertainment"

    indexer_client = httpx.Client(base_url=INDEXER_BASE, timeout=10.0)
    try:
        response = indexer_client.post(
            "/v1/fingerprints/index",
            json={
                "fingerprint_hash": fingerprint_hash,
                "content_id": content_id,
                "title": title,
                "network": network,
                "genre": genre,
                "duration_seconds": 3600,
                "aired_at_utc": int(time.time())
            }
        )
        assert response.status_code in (200, 201), f"Failed to index reference fingerprint: {response.text}"
    finally:
        indexer_client.close()

    return (fingerprint_hash, content_id, title, network, genre)


@pytest.fixture
def wait_for_service():
    """
    Polls /health endpoint until 200 or raises TimeoutError.
    Usage: wait_for_service("http://localhost:8080", timeout=30)
    """
    def _wait(url: str, timeout: int = 30):
        start_time = time.time()
        client = httpx.Client(timeout=5.0)

        while time.time() - start_time < timeout:
            try:
                response = client.get(f"{url}/health")
                if response.status_code == 200:
                    return
            except (httpx.RequestError, httpx.TimeoutException):
                pass

            time.sleep(0.5)

        client.close()
        raise TimeoutError(f"Service at {url} did not become healthy within {timeout}s")

    return _wait


# Session-scoped fixtures for HTTP clients
@pytest.fixture(scope="session")
def ingest_client() -> httpx.Client:
    """Ingestor service client."""
    return httpx.Client(base_url=INGEST_BASE, timeout=10.0)


@pytest.fixture(scope="session")
def indexer_client() -> httpx.Client:
    """Indexer service client."""
    return httpx.Client(base_url=INDEXER_BASE, timeout=10.0)


@pytest.fixture(scope="session")
def api_client() -> httpx.Client:
    """Advertiser API service client."""
    return httpx.Client(base_url=API_BASE, timeout=10.0)


@pytest.fixture(scope="session")
def privacy_client() -> httpx.Client:
    """Privacy service client."""
    return httpx.Client(base_url=PRIVACY_BASE, timeout=10.0)


@pytest.fixture(scope="session")
def billing_client() -> httpx.Client:
    """Billing service client."""
    return httpx.Client(base_url=BILLING_BASE, timeout=10.0)


# Helper fixtures
@pytest.fixture
def random_fingerprints() -> list:
    """Generate a list of random fingerprints for testing."""
    return [hashlib.sha256(str(random.random()).encode()).hexdigest() for _ in range(100)]


@pytest.fixture
def valid_batch_payload(test_device_id, test_fingerprint) -> dict:
    """
    Returns a valid fingerprint batch payload.
    """
    return {
        "batch": [
            {
                "device_id": test_device_id,
                "fingerprint_hash": test_fingerprint,
                "timestamp_utc": int(time.time()),
                "manufacturer": "LG",
                "model": "OLED55",
                "ip_address": "192.168.1.100"
            }
        ]
    }
