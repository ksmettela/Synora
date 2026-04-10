"""
Integration tests for privacy-service (Component G).
"""
import pytest
import httpx
import time
import hashlib
import json


@pytest.mark.integration
class TestConsentManagement:
    """Consent recording and retrieval."""

    def test_record_opt_in_consent(self, privacy_client, test_device_id):
        """Test recording opt-in consent returns 201."""
        response = privacy_client.post(
            "/v1/consent/record",
            json={
                "device_id": test_device_id,
                "opted_in": True,
                "consent_timestamp_utc": int(time.time())
            }
        )
        assert response.status_code in (200, 201)
        data = response.json()
        assert data["device_id"] == test_device_id

    def test_record_opt_out_consent(self, privacy_client, test_device_id):
        """Test recording opt-out consent returns 201."""
        response = privacy_client.post(
            "/v1/consent/record",
            json={
                "device_id": test_device_id,
                "opted_in": False,
                "consent_timestamp_utc": int(time.time())
            }
        )
        assert response.status_code in (200, 201)
        data = response.json()
        assert data["device_id"] == test_device_id

    def test_get_consent_status(self, privacy_client, test_device_id):
        """Test retrieving consent status for a device."""
        # Record opt-in
        privacy_client.post(
            "/v1/consent/record",
            json={
                "device_id": test_device_id,
                "opted_in": True,
                "consent_timestamp_utc": int(time.time())
            }
        )

        # Get consent status
        response = privacy_client.get(
            f"/v1/consent/{test_device_id}"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["device_id"] == test_device_id
        assert data["opted_in"] is True

    def test_consent_unknown_device_returns_404(self, privacy_client):
        """Test getting consent for unknown device returns 404."""
        unknown_device = hashlib.sha256(b"unknown-consent-device").hexdigest()
        response = privacy_client.get(
            f"/v1/consent/{unknown_device}"
        )
        assert response.status_code == 404


@pytest.mark.integration
class TestOptOut:
    """Device opt-out functionality."""

    def test_opt_out_accepted(self, privacy_client, test_device_id, redis_client):
        """Test opt-out request returns 202 with job_id."""
        response = privacy_client.post(
            "/v1/privacy/opt-out",
            json={"device_id": test_device_id}
        )
        assert response.status_code == 202
        data = response.json()
        assert "job_id" in data
        assert "estimated_completion_utc" in data

    def test_opt_out_removes_device_from_redis_segments(self, privacy_client, test_device_id, redis_client):
        """Test opt-out removes device from Redis segment sets."""
        # Seed device in multiple Redis segments
        segments = ["sports-fans", "movie-watchers", "news-consumers"]
        for segment in segments:
            redis_client.sadd(f"segment:{segment}", test_device_id)

        # Verify device is in segments
        for segment in segments:
            assert redis_client.sismember(f"segment:{segment}", test_device_id)

        # Opt out
        response = privacy_client.post(
            "/v1/privacy/opt-out",
            json={"device_id": test_device_id}
        )
        assert response.status_code == 202

        # Wait up to 5 seconds for opt-out to process
        start_time = time.time()
        while time.time() - start_time < 5:
            in_any_segment = False
            for segment in segments:
                if redis_client.sismember(f"segment:{segment}", test_device_id):
                    in_any_segment = True
                    break

            if not in_any_segment:
                # Successfully removed from all segments
                break

            time.sleep(0.1)

        # Verify device removed from all segments
        for segment in segments:
            assert not redis_client.sismember(f"segment:{segment}", test_device_id)

    def test_opt_out_returns_estimated_completion_time(self, privacy_client, test_device_id):
        """Test opt-out response includes estimated completion time."""
        response = privacy_client.post(
            "/v1/privacy/opt-out",
            json={"device_id": test_device_id}
        )
        assert response.status_code == 202
        data = response.json()
        assert "estimated_completion_utc" in data

        # Verify estimated time is within 24 hours
        estimated_time = data["estimated_completion_utc"]
        current_time = int(time.time())
        time_diff = estimated_time - current_time
        assert 0 < time_diff <= 86400, "Estimated completion time not within 24 hours"

    def test_duplicate_opt_out_is_idempotent(self, privacy_client, test_device_id):
        """Test opt-out twice returns 202 both times."""
        response1 = privacy_client.post(
            "/v1/privacy/opt-out",
            json={"device_id": test_device_id}
        )
        assert response1.status_code == 202

        response2 = privacy_client.post(
            "/v1/privacy/opt-out",
            json={"device_id": test_device_id}
        )
        assert response2.status_code == 202


@pytest.mark.integration
class TestGDPR:
    """GDPR compliance features."""

    def test_data_export_returns_json(self, privacy_client, test_device_id):
        """Test data export returns JSON with consent data."""
        # Record some consent data first
        privacy_client.post(
            "/v1/consent/record",
            json={
                "device_id": test_device_id,
                "opted_in": True,
                "consent_timestamp_utc": int(time.time())
            }
        )

        # Export data
        response = privacy_client.get(
            f"/v1/privacy/data-export?device_id={test_device_id}"
        )
        assert response.status_code == 200
        data = response.json()
        assert "device_id" in data
        assert data["device_id"] == test_device_id

    def test_erasure_request_accepted(self, privacy_client, test_device_id):
        """Test erasure request returns 202 with 72h deadline."""
        response = privacy_client.delete(
            "/v1/privacy/erase",
            json={"device_id": test_device_id}
        )
        assert response.status_code == 202
        data = response.json()
        assert "job_id" in data
        assert "erasure_deadline_utc" in data

        # Verify deadline is 72 hours or less
        deadline = data["erasure_deadline_utc"]
        current_time = int(time.time())
        time_diff = deadline - current_time
        assert 0 < time_diff <= 259200, "Erasure deadline not within 72 hours"


@pytest.mark.integration
class TestTCF:
    """TCF 2.2 consent string handling."""

    def test_valid_tcf_string_accepted(self, privacy_client, test_device_id):
        """Test valid TCF 2.2 string is accepted."""
        # Minimal valid TCF string (base64)
        tcf_string = "COwyDgAOwyDAAAEsACEsAA=="

        response = privacy_client.post(
            "/v1/privacy/tcf",
            json={
                "device_id": test_device_id,
                "tcf_consent_string": tcf_string
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "parsed_purposes" in data

    def test_invalid_tcf_string_rejected(self, privacy_client, test_device_id):
        """Test invalid TCF string is rejected."""
        response = privacy_client.post(
            "/v1/privacy/tcf",
            json={
                "device_id": test_device_id,
                "tcf_consent_string": "not-valid-base64-\!\!\!"
            }
        )
        assert response.status_code == 400
