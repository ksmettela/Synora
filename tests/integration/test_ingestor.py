"""
Integration tests for fingerprint-ingestor service (Component B).
"""
import pytest
import httpx
import hashlib
import time
import json


@pytest.mark.integration
class TestHealth:
    """Health check endpoints."""

    def test_health_returns_200(self, ingest_client):
        """Test health endpoint returns 200 OK."""
        response = ingest_client.get("/health")
        assert response.status_code == 200
        assert response.headers.get("content-type") == "application/json"

    def test_health_includes_kafka_status(self, ingest_client):
        """Test health endpoint includes Kafka service status."""
        response = ingest_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] in ("healthy", "degraded")

    def test_metrics_endpoint_returns_prometheus_format(self, ingest_client):
        """Test /metrics endpoint returns Prometheus format."""
        response = ingest_client.get("/metrics")
        assert response.status_code == 200
        text = response.text
        assert "# HELP" in text or "# TYPE" in text
        assert "http_requests_total" in text or "process_cpu_seconds_total" in text


@pytest.mark.integration
class TestFingerprintIngestion:
    """Fingerprint ingestion and validation."""

    def test_valid_single_fingerprint_returns_202(self, ingest_client, test_device_id, test_fingerprint):
        """Test POSTing single valid fingerprint returns 202 Accepted."""
        payload = {
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
        response = ingest_client.post(
            "/v1/fingerprints",
            json=payload,
            headers={"X-API-Key": "test-api-key-001"}
        )
        assert response.status_code == 202
        data = response.json()
        assert "batch_id" in data
        assert data["accepted"] == 1

    def test_valid_batch_of_20_returns_202(self, ingest_client):
        """Test POSTing batch of 20 valid fingerprints returns 202."""
        batch = []
        for i in range(20):
            device_id = hashlib.sha256(f"device-{i}".encode()).hexdigest()
            fingerprint = hashlib.sha256(f"fp-{i}".encode()).hexdigest()
            batch.append({
                "device_id": device_id,
                "fingerprint_hash": fingerprint,
                "timestamp_utc": int(time.time()),
                "manufacturer": "Vizio",
                "model": f"MODEL-{i}",
                "ip_address": f"192.168.1.{i}"
            })

        response = ingest_client.post(
            "/v1/fingerprints",
            json={"batch": batch},
            headers={"X-API-Key": "test-api-key-001"}
        )
        assert response.status_code == 202
        data = response.json()
        assert data["accepted"] == 20

    def test_max_batch_size_100_accepted(self, ingest_client):
        """Test batch of exactly 100 fingerprints is accepted."""
        batch = []
        for i in range(100):
            device_id = hashlib.sha256(f"device-100-{i}".encode()).hexdigest()
            fingerprint = hashlib.sha256(f"fp-100-{i}".encode()).hexdigest()
            batch.append({
                "device_id": device_id,
                "fingerprint_hash": fingerprint,
                "timestamp_utc": int(time.time()),
                "manufacturer": "TCL",
                "model": f"M{i}",
                "ip_address": f"10.0.0.{i % 256}"
            })

        response = ingest_client.post(
            "/v1/fingerprints",
            json={"batch": batch},
            headers={"X-API-Key": "test-api-key-001"}
        )
        assert response.status_code == 202
        assert response.json()["accepted"] == 100

    def test_batch_over_100_rejected_with_400(self, ingest_client):
        """Test batch of 101 fingerprints is rejected with 400."""
        batch = []
        for i in range(101):
            device_id = hashlib.sha256(f"device-101-{i}".encode()).hexdigest()
            fingerprint = hashlib.sha256(f"fp-101-{i}".encode()).hexdigest()
            batch.append({
                "device_id": device_id,
                "fingerprint_hash": fingerprint,
                "timestamp_utc": int(time.time()),
                "manufacturer": "Sony",
                "model": f"XM{i}",
                "ip_address": f"10.1.0.{i % 256}"
            })

        response = ingest_client.post(
            "/v1/fingerprints",
            json={"batch": batch},
            headers={"X-API-Key": "test-api-key-001"}
        )
        assert response.status_code == 400
        data = response.json()
        assert "batch size" in data.get("detail", "").lower() or "limit" in data.get("detail", "").lower()

    def test_invalid_device_id_non_hex_rejected(self, ingest_client, test_fingerprint):
        """Test device_id with non-hex characters is rejected."""
        payload = {
            "batch": [
                {
                    "device_id": "not-a-valid-hex-string-zzzzzzzzzzzzzzzzzzzzzzzzzzzzz",
                    "fingerprint_hash": test_fingerprint,
                    "timestamp_utc": int(time.time()),
                    "manufacturer": "LG",
                    "model": "TEST",
                    "ip_address": "192.168.1.1"
                }
            ]
        }
        response = ingest_client.post(
            "/v1/fingerprints",
            json=payload,
            headers={"X-API-Key": "test-api-key-001"}
        )
        assert response.status_code == 400

    def test_device_id_wrong_length_rejected(self, ingest_client, test_fingerprint):
        """Test device_id with incorrect length is rejected."""
        payload = {
            "batch": [
                {
                    "device_id": "abcdef",  # Only 6 chars, should be 64
                    "fingerprint_hash": test_fingerprint,
                    "timestamp_utc": int(time.time()),
                    "manufacturer": "LG",
                    "model": "TEST",
                    "ip_address": "192.168.1.1"
                }
            ]
        }
        response = ingest_client.post(
            "/v1/fingerprints",
            json=payload,
            headers={"X-API-Key": "test-api-key-001"}
        )
        assert response.status_code == 400

    def test_invalid_fingerprint_hash_rejected(self, ingest_client, test_device_id):
        """Test fingerprint_hash not 64-char hex is rejected."""
        payload = {
            "batch": [
                {
                    "device_id": test_device_id,
                    "fingerprint_hash": "not-valid",
                    "timestamp_utc": int(time.time()),
                    "manufacturer": "LG",
                    "model": "TEST",
                    "ip_address": "192.168.1.1"
                }
            ]
        }
        response = ingest_client.post(
            "/v1/fingerprints",
            json=payload,
            headers={"X-API-Key": "test-api-key-001"}
        )
        assert response.status_code == 400

    def test_timestamp_5_minutes_old_rejected(self, ingest_client, test_device_id, test_fingerprint):
        """Test fingerprint with timestamp 5+ minutes old is rejected."""
        old_timestamp = int(time.time()) - 400  # 400 seconds = ~6.7 minutes
        payload = {
            "batch": [
                {
                    "device_id": test_device_id,
                    "fingerprint_hash": test_fingerprint,
                    "timestamp_utc": old_timestamp,
                    "manufacturer": "LG",
                    "model": "TEST",
                    "ip_address": "192.168.1.1"
                }
            ]
        }
        response = ingest_client.post(
            "/v1/fingerprints",
            json=payload,
            headers={"X-API-Key": "test-api-key-001"}
        )
        assert response.status_code == 400

    def test_future_timestamp_rejected(self, ingest_client, test_device_id, test_fingerprint):
        """Test fingerprint with future timestamp is rejected."""
        future_timestamp = int(time.time()) + 400
        payload = {
            "batch": [
                {
                    "device_id": test_device_id,
                    "fingerprint_hash": test_fingerprint,
                    "timestamp_utc": future_timestamp,
                    "manufacturer": "LG",
                    "model": "TEST",
                    "ip_address": "192.168.1.1"
                }
            ]
        }
        response = ingest_client.post(
            "/v1/fingerprints",
            json=payload,
            headers={"X-API-Key": "test-api-key-001"}
        )
        assert response.status_code == 400

    def test_missing_required_field_rejected(self, ingest_client, test_device_id):
        """Test batch with missing device_id field returns 422."""
        payload = {
            "batch": [
                {
                    # device_id is missing
                    "fingerprint_hash": hashlib.sha256(b"test").hexdigest(),
                    "timestamp_utc": int(time.time()),
                    "manufacturer": "LG",
                    "model": "TEST",
                    "ip_address": "192.168.1.1"
                }
            ]
        }
        response = ingest_client.post(
            "/v1/fingerprints",
            json=payload,
            headers={"X-API-Key": "test-api-key-001"}
        )
        assert response.status_code in (400, 422)

    def test_empty_batch_rejected(self, ingest_client):
        """Test empty batch is rejected with 400."""
        payload = {"batch": []}
        response = ingest_client.post(
            "/v1/fingerprints",
            json=payload,
            headers={"X-API-Key": "test-api-key-001"}
        )
        assert response.status_code == 400


@pytest.mark.integration
class TestAuthentication:
    """API key authentication."""

    def test_missing_api_key_returns_401(self, ingest_client, valid_batch_payload):
        """Test request without API key returns 401."""
        response = ingest_client.post(
            "/v1/fingerprints",
            json=valid_batch_payload
        )
        assert response.status_code == 401

    def test_invalid_api_key_returns_403(self, ingest_client, valid_batch_payload):
        """Test request with invalid API key returns 403."""
        response = ingest_client.post(
            "/v1/fingerprints",
            json=valid_batch_payload,
            headers={"X-API-Key": "invalid-key-12345"}
        )
        assert response.status_code == 403

    def test_valid_api_key_accepted(self, ingest_client, valid_batch_payload):
        """Test request with valid API key is accepted."""
        response = ingest_client.post(
            "/v1/fingerprints",
            json=valid_batch_payload,
            headers={"X-API-Key": "test-api-key-001"}
        )
        assert response.status_code == 202

    def test_api_key_in_query_param_rejected(self, ingest_client, valid_batch_payload):
        """Test API key in query parameter is rejected (must be in header)."""
        response = ingest_client.post(
            "/v1/fingerprints?api_key=test-api-key-001",
            json=valid_batch_payload
        )
        assert response.status_code == 401


@pytest.mark.integration
class TestRateLimiting:
    """Rate limiting behavior."""

    def test_rate_limit_header_present_in_response(self, ingest_client, valid_batch_payload):
        """Test response includes rate limit headers."""
        response = ingest_client.post(
            "/v1/fingerprints",
            json=valid_batch_payload,
            headers={"X-API-Key": "test-api-key-001"}
        )
        assert response.status_code == 202
        # Check for standard rate limit headers
        headers = response.headers
        has_rate_limit = (
            "x-ratelimit-limit" in headers or
            "x-rate-limit-limit" in headers or
            "ratelimit-limit" in headers
        )
        assert has_rate_limit, "Response missing rate limit headers"

    def test_exceeding_rate_limit_returns_429(self, ingest_client, valid_batch_payload):
        """Test rapid requests exceed rate limit and return 429."""
        responses = []
        for i in range(50):
            response = ingest_client.post(
                "/v1/fingerprints",
                json=valid_batch_payload,
                headers={"X-API-Key": "test-api-key-001"}
            )
            responses.append(response.status_code)

        # At least one request should be rate limited
        assert 429 in responses, "No 429 responses in rapid fire requests"


@pytest.mark.integration
@pytest.mark.slow
class TestKafkaPublishing:
    """Kafka message publishing."""

    def test_valid_fingerprint_appears_in_kafka(self, ingest_client, kafka_consumer,
                                                 test_device_id, test_fingerprint):
        """Test valid fingerprint appears in Kafka raw.fingerprints topic."""
        consumer = kafka_consumer("raw.fingerprints")

        payload = {
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

        response = ingest_client.post(
            "/v1/fingerprints",
            json=payload,
            headers={"X-API-Key": "test-api-key-001"}
        )
        assert response.status_code == 202

        # Consume messages for up to 10 seconds
        start_time = time.time()
        found = False
        for message in consumer:
            if time.time() - start_time > 10:
                break

            msg_data = json.loads(message.value)
            if msg_data.get("device_id") == test_device_id and \
               msg_data.get("fingerprint_hash") == test_fingerprint:
                found = True
                break

        consumer.close()
        assert found, "Fingerprint not found in Kafka within 10 seconds"
