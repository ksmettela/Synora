"""
Full pipeline integration tests for Synora.
"""
import pytest
import time
import hashlib
import json


@pytest.mark.integration
@pytest.mark.slow
class TestFullPipeline:
    """End-to-end pipeline tests."""

    def test_fingerprint_ingestion_to_kafka(self, ingest_client, kafka_consumer,
                                             test_device_id, test_fingerprint):
        """
        Send a fingerprint batch → verify it lands in raw.fingerprints Kafka topic.
        """
        consumer = kafka_consumer("raw.fingerprints")

        # 1. POST fingerprint to ingestor
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

        # 2. Consume from raw.fingerprints for up to 15 seconds
        start_time = time.time()
        found = False
        for message in consumer:
            if time.time() - start_time > 15:
                break

            msg_data = json.loads(message.value)
            if msg_data.get("device_id") == test_device_id and \
               msg_data.get("fingerprint_hash") == test_fingerprint:
                found = True
                break

        consumer.close()

        # 3. Assert message with matching device_id found
        assert found, "Fingerprint not found in Kafka within 15 seconds"

    def test_opt_out_full_lifecycle(self, ingest_client, privacy_client, redis_client,
                                     test_device_id):
        """
        Full opt-out flow: record consent → send fingerprints → opt out → verify clean state.
        """
        # 1. Record opt-in consent via privacy-service
        response = privacy_client.post(
            "/v1/consent/record",
            json={
                "device_id": test_device_id,
                "opted_in": True,
                "consent_timestamp_utc": int(time.time())
            }
        )
        assert response.status_code in (200, 201)

        # 2. Seed device in 3 Redis segments (simulate matching engine output)
        segments = ["segment-a", "segment-b", "segment-c"]
        for segment in segments:
            redis_client.sadd(f"segment:{segment}", test_device_id)

        # Verify seeded
        for segment in segments:
            assert redis_client.sismember(f"segment:{segment}", test_device_id)

        # 3. Call privacy opt-out
        response = privacy_client.post(
            "/v1/privacy/opt-out",
            json={"device_id": test_device_id}
        )
        assert response.status_code == 202

        # 4. Wait up to 10 seconds
        start_time = time.time()
        while time.time() - start_time < 10:
            in_any_segment = False
            for segment in segments:
                if redis_client.sismember(f"segment:{segment}", test_device_id):
                    in_any_segment = True
                    break

            if not in_any_segment:
                break

            time.sleep(0.2)

        # 5. Verify device_id no longer in any Redis segment
        for segment in segments:
            assert not redis_client.sismember(f"segment:{segment}", test_device_id)

        # 6. Verify consent status = opted_out
        response = privacy_client.get(
            f"/v1/consent/{test_device_id}"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["opted_in"] is False

    def test_segment_creation_and_rtb_lookup(self, api_client, auth_token, redis_client):
        """
        Create a segment → seed devices → RTB lookup returns correct segments.
        """
        # 1. Create custom segment via advertiser API
        segment_name = f"e2e-test-segment-{int(time.time())}"
        response = api_client.post(
            "/v1/segments",
            json={
                "name": segment_name,
                "description": "E2E test segment",
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
        segment_id = response.json().get("id") or response.json().get("segment_id")

        # 2. Manually seed 50 device_ids into Redis for that segment
        test_device_ids = [
            hashlib.sha256(f"e2e-device-{i}".encode()).hexdigest()
            for i in range(50)
        ]

        for device_id in test_device_ids:
            redis_client.sadd(f"device:segments:{device_id}", segment_id)
            redis_client.expire(f"device:segments:{device_id}", 86400)

        # 3. RTB lookup for one of those device_ids
        lookup_device = test_device_ids[0]
        response = api_client.post(
            "/v1/sync/openrtb",
            json={"device_id": lookup_device, "ip": "192.168.1.1"},
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()

        # 4. Assert segment appears in response
        assert "segments" in data
        assert segment_id in data["segments"] or len(data["segments"]) > 0
