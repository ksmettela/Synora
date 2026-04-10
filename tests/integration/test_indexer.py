"""
Integration tests for fingerprint-indexer service (Component C1).
"""
import pytest
import httpx
import hashlib
import time
import json


@pytest.mark.integration
class TestFingerprintIndexing:
    """Fingerprint indexing and lookup."""

    def test_index_new_fingerprint(self, indexer_client):
        """Test indexing a new fingerprint returns 201 Created."""
        fingerprint_hash = hashlib.sha256(b"test-fp-unique-001").hexdigest()
        content_id = f"content-{int(time.time())}-001"

        response = indexer_client.post(
            "/v1/fingerprints/index",
            json={
                "fingerprint_hash": fingerprint_hash,
                "content_id": content_id,
                "title": "Test Show",
                "network": "HBO",
                "genre": "Drama",
                "duration_seconds": 3600,
                "aired_at_utc": int(time.time())
            }
        )
        assert response.status_code in (200, 201)
        data = response.json()
        assert data["fingerprint_hash"] == fingerprint_hash
        assert data["content_id"] == content_id

    def test_exact_lookup_finds_match(self, indexer_client, reference_fingerprint):
        """Test exact fingerprint lookup finds match."""
        fp_hash, content_id, title, network, genre = reference_fingerprint

        response = indexer_client.post(
            "/v1/fingerprints/lookup",
            json={"fingerprint_hash": fp_hash}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["found"] is True
        assert data["content_id"] == content_id
        assert data["title"] == title
        assert data["network"] == network

    def test_hamming_distance_1_finds_match(self, indexer_client, reference_fingerprint):
        """Test lookup with 1 bit flip still finds match (within 8-bit tolerance)."""
        fp_hash, content_id, _, _, _ = reference_fingerprint

        # Flip the first bit in the hash
        fp_int = int(fp_hash, 16)
        fp_flipped = hex(fp_int ^ 1)[2:].zfill(64)

        response = indexer_client.post(
            "/v1/fingerprints/lookup",
            json={"fingerprint_hash": fp_flipped}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["found"] is True
        assert data["content_id"] == content_id

    def test_hamming_distance_8_finds_match(self, indexer_client, reference_fingerprint):
        """Test lookup with 8 bits flipped still finds match."""
        fp_hash, content_id, _, _, _ = reference_fingerprint

        # Flip exactly 8 bits
        fp_int = int(fp_hash, 16)
        # Flip bits 0-7
        for i in range(8):
            fp_int ^= (1 << i)
        fp_flipped = hex(fp_int)[2:].zfill(64)

        response = indexer_client.post(
            "/v1/fingerprints/lookup",
            json={"fingerprint_hash": fp_flipped}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["found"] is True
        assert data["content_id"] == content_id

    def test_hamming_distance_9_no_match(self, indexer_client, reference_fingerprint):
        """Test lookup with 9 bits flipped does NOT find match."""
        fp_hash, _, _, _, _ = reference_fingerprint

        # Flip 9 bits - should exceed tolerance
        fp_int = int(fp_hash, 16)
        for i in range(9):
            fp_int ^= (1 << i)
        fp_flipped = hex(fp_int)[2:].zfill(64)

        response = indexer_client.post(
            "/v1/fingerprints/lookup",
            json={"fingerprint_hash": fp_flipped}
        )
        assert response.status_code == 200
        data = response.json()
        # Should not match because hamming distance > 8
        assert data["found"] is False

    def test_completely_unknown_fingerprint_returns_no_match(self, indexer_client):
        """Test lookup of never-indexed fingerprint returns no match."""
        random_hash = hashlib.sha256(b"completely-random-unknown-fp").hexdigest()

        response = indexer_client.post(
            "/v1/fingerprints/lookup",
            json={"fingerprint_hash": random_hash}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["found"] is False

    def test_stats_endpoint_returns_network_counts(self, indexer_client):
        """Test /stats endpoint returns network counts."""
        response = indexer_client.get("/v1/fingerprints/stats")
        assert response.status_code == 200
        data = response.json()
        assert "networks" in data
        assert isinstance(data["networks"], dict)
        # Should have at least one network (from reference_fingerprint)
        assert len(data["networks"]) > 0

    def test_duplicate_index_is_idempotent(self, indexer_client, reference_fingerprint):
        """Test indexing same fingerprint twice is idempotent."""
        fp_hash, content_id, title, network, genre = reference_fingerprint

        # Index same fingerprint again
        response = indexer_client.post(
            "/v1/fingerprints/index",
            json={
                "fingerprint_hash": fp_hash,
                "content_id": content_id,
                "title": title,
                "network": network,
                "genre": genre,
                "duration_seconds": 3600,
                "aired_at_utc": int(time.time())
            }
        )
        assert response.status_code in (200, 201)

        # Lookup should still return only one result
        response = indexer_client.post(
            "/v1/fingerprints/lookup",
            json={"fingerprint_hash": fp_hash}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["found"] is True
        assert data["content_id"] == content_id
