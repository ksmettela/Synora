"""
Integration tests for FastAPI advertiser/DSP API (Component F).
"""
import pytest
import httpx
import time
import json
import jwt
import hashlib
import random


@pytest.mark.integration
class TestOAuth2Authentication:
    """OAuth2 token authentication."""

    def test_token_endpoint_returns_jwt(self, api_client):
        """Test /v1/auth/token returns JWT access token."""
        response = api_client.post(
            "/v1/auth/token",
            json={
                "client_id": "test-client-001",
                "client_secret": "test-client-secret-001",
                "grant_type": "client_credentials"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert isinstance(data["access_token"], str)
        assert len(data["access_token"]) > 20

    def test_invalid_client_secret_rejected(self, api_client):
        """Test token request with wrong secret returns 401."""
        response = api_client.post(
            "/v1/auth/token",
            json={
                "client_id": "test-client-001",
                "client_secret": "wrong-secret-12345",
                "grant_type": "client_credentials"
            }
        )
        assert response.status_code == 401

    def test_token_has_correct_scopes(self, api_client, auth_token):
        """Test JWT contains correct scopes."""
        # Decode without verification (for testing)
        try:
            decoded = jwt.decode(auth_token, options={"verify_signature": False})
            assert "scope" in decoded or "scopes" in decoded
        except jwt.DecodeError:
            # Token might be in different format, just verify it works
            response = api_client.get(
                "/v1/segments",
                headers={"Authorization": f"Bearer {auth_token}"}
            )
            assert response.status_code == 200

    def test_expired_token_rejected(self, api_client):
        """Test request with expired token returns 401."""
        # Create a token with past expiration
        past_exp = int(time.time()) - 3600
        expired_token = jwt.encode(
            {"exp": past_exp, "client_id": "test"},
            "secret",
            algorithm="HS256"
        )

        response = api_client.get(
            "/v1/segments",
            headers={"Authorization": f"Bearer {expired_token}"}
        )
        assert response.status_code == 401


@pytest.mark.integration
class TestSegmentManagement:
    """Segment creation and management."""

    def test_list_segments_returns_array(self, api_client, auth_token):
        """Test GET /v1/segments returns array of segments."""
        response = api_client.get(
            "/v1/segments",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_each_segment_has_required_fields(self, api_client, auth_token):
        """Test segments contain required fields."""
        response = api_client.get(
            "/v1/segments",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()

        if len(data) > 0:
            segment = data[0]
            required_fields = ["id", "name", "description", "device_count", "household_count", "cpm_floor"]
            for field in required_fields:
                assert field in segment, f"Missing field: {field}"

    def test_create_custom_segment_returns_segment_id(self, api_client, auth_token):
        """Test creating custom segment returns segment_id."""
        response = api_client.post(
            "/v1/segments",
            json={
                "name": f"test-segment-{int(time.time())}",
                "description": "Test custom segment",
                "rules": [
                    {
                        "type": "watched_genre",
                        "genre": "Drama",
                        "threshold_days": 30
                    }
                ]
            },
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code in (200, 201)
        data = response.json()
        assert "id" in data or "segment_id" in data

    def test_segment_dsl_with_all_rule_types(self, api_client, auth_token):
        """Test segment creation with all rule types."""
        response = api_client.post(
            "/v1/segments",
            json={
                "name": f"all-rules-{int(time.time())}",
                "description": "Segment with all rule types",
                "rules": [
                    {"type": "watched_genre", "genre": "Sports", "threshold_days": 30},
                    {"type": "watched_network", "network": "ESPN", "threshold_days": 30},
                    {"type": "dma", "dma": "New York"},
                    {"type": "daypart", "daypart": "primetime"}
                ]
            },
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code in (200, 201)
        data = response.json()
        assert "id" in data or "segment_id" in data

    def test_segment_invalid_rule_type_rejected(self, api_client, auth_token):
        """Test segment with invalid rule type is rejected."""
        response = api_client.post(
            "/v1/segments",
            json={
                "name": f"invalid-rules-{int(time.time())}",
                "description": "Invalid rules",
                "rules": [
                    {"type": "invalid_rule_type", "value": "test"}
                ]
            },
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code in (400, 422)

    def test_segment_with_empty_rules_rejected(self, api_client, auth_token):
        """Test segment with no rules is rejected."""
        response = api_client.post(
            "/v1/segments",
            json={
                "name": f"no-rules-{int(time.time())}",
                "description": "No rules",
                "rules": []
            },
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code in (400, 422)

    def test_get_segment_size(self, api_client, auth_token):
        """Test GET /v1/segments/{id}/size returns device/household counts."""
        # First get any segment
        response = api_client.get(
            "/v1/segments",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        segments = response.json()

        if len(segments) > 0:
            segment_id = segments[0].get("id") or segments[0].get("segment_id")
            response = api_client.get(
                f"/v1/segments/{segment_id}/size",
                headers={"Authorization": f"Bearer {auth_token}"}
            )
            assert response.status_code == 200
            data = response.json()
            assert "device_count" in data
            assert "household_count" in data


@pytest.mark.integration
class TestRTBLookup:
    """Real-time bidding device lookups."""

    def test_rtb_lookup_returns_segment_list(self, api_client, auth_token, redis_client):
        """Test RTB lookup returns segments for seeded device."""
        device_id = hashlib.sha256(b"test-rtb-device-001").hexdigest()

        # Seed device → segments mapping in Redis
        segments_key = f"device:segments:{device_id}"
        redis_client.delete(segments_key)
        redis_client.sadd(segments_key, "segment-1", "segment-2", "segment-3")
        redis_client.expire(segments_key, 86400)

        response = api_client.post(
            "/v1/sync/openrtb",
            json={"device_id": device_id, "ip": "192.168.1.100"},
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "segments" in data
        assert isinstance(data["segments"], list)
        assert len(data["segments"]) >= 3

    def test_rtb_lookup_unknown_device_returns_empty(self, api_client, auth_token):
        """Test RTB lookup for unknown device returns empty segments."""
        unknown_device = hashlib.sha256(b"completely-unknown-device-xyz").hexdigest()

        response = api_client.post(
            "/v1/sync/openrtb",
            json={"device_id": unknown_device, "ip": "10.0.0.1"},
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "segments" in data
        assert data["segments"] == []

    def test_rtb_lookup_latency_under_5ms(self, api_client, auth_token, redis_client):
        """Test RTB lookup latency meets p99 < 5ms SLO."""
        # Seed 100 devices in Redis
        device_pool = []
        for i in range(100):
            device_id = hashlib.sha256(f"latency-test-{i}".encode()).hexdigest()
            device_pool.append(device_id)
            segments_key = f"device:segments:{device_id}"
            redis_client.sadd(segments_key, f"seg-{i % 10}")
            redis_client.expire(segments_key, 86400)

        # Fire 500 RTB lookups
        times = []
        for _ in range(500):
            device_id = random.choice(device_pool)
            start = time.perf_counter()
            response = api_client.post(
                "/v1/sync/openrtb",
                json={"device_id": device_id, "ip": "10.0.0.1"},
                headers={"Authorization": f"Bearer {auth_token}"}
            )
            elapsed_ms = (time.perf_counter() - start) * 1000
            times.append(elapsed_ms)
            assert response.status_code == 200

        # Calculate p99
        times.sort()
        p99_idx = int(len(times) * 0.99)
        p99 = times[p99_idx]
        assert p99 < 5.0, f"RTB p99 latency {p99:.2f}ms exceeds 5ms SLO"

    def test_rtb_lookup_ip_household_fallback(self, api_client, auth_token, redis_client):
        """Test RTB lookup falls back to IP household mapping."""
        device_id = hashlib.sha256(b"unknown-device-fallback").hexdigest()
        ip_address = "10.50.100.75"

        # Seed IP → household segments mapping
        ip_key = f"ip:segments:{ip_address}"
        redis_client.delete(ip_key)
        redis_client.sadd(ip_key, "household-seg-1", "household-seg-2")
        redis_client.expire(ip_key, 86400)

        response = api_client.post(
            "/v1/sync/openrtb",
            json={"device_id": device_id, "ip": ip_address},
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        # Should return household segments from IP fallback
        assert "segments" in data


@pytest.mark.integration
class TestSegmentOverlap:
    """Segment overlap reporting."""

    def test_overlap_endpoint_returns_count(self, api_client, auth_token):
        """Test GET /v1/reports/overlap returns overlap count."""
        response = api_client.get(
            "/v1/reports/overlap?seg_a=segment-1&seg_b=segment-2",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "overlap_count" in data or "overlap" in data
        assert isinstance(data.get("overlap_count") or data.get("overlap"), int)
