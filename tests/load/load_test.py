"""
Load tests for Synora platform using Locust.
Run: locust -f tests/load/load_test.py --host=http://localhost:8080 -u 100 -r 10 -t 5m
"""
from locust import HttpUser, task, between, events
from locust.contrib.fasthttp import FastHttpUser
import random
import time
import json
import hashlib


class IngestUser(HttpUser):
    """
    Simulates SDK devices (TVs, set-top boxes) sending fingerprints to ingestor.
    Realistic load: 100-1000 devices each sending 20 fingerprints per batch, every 60 seconds.
    """
    wait_time = between(30, 90)  # Realistic: devices send batches occasionally
    api_key = "test_ingest_key_12345"

    def on_start(self):
        """Generate a stable device ID for this user."""
        user_id = self.client.base_url.split("://")[1].replace(":", "_") + "_" + str(self.user_id)
        self.device_id = hashlib.sha256(user_id.encode()).hexdigest()

    def generate_fingerprint(self):
        """Generate a random hex fingerprint."""
        random_bytes = "".join(format(random.randint(0, 255), '02x') for _ in range(32))
        return random_bytes

    def generate_batch(self):
        """Generate a batch of 20 fingerprints."""
        networks = ["espn", "hbo", "netflix", "hulu", "disney", "cnn", "bbc", "itv"]
        return {
            "device_id": self.device_id,
            "fingerprints": [
                {
                    "network": random.choice(networks),
                    "fingerprint": self.generate_fingerprint(),
                    "timestamp": int(time.time()),
                    "confidence": round(random.uniform(0.75, 0.99), 2)
                }
                for _ in range(20)
            ]
        }

    @task(10)
    def send_fingerprints(self):
        """POST /v1/fingerprints with batch of 20"""
        batch = self.generate_batch()
        with self.client.post(
            "/v1/fingerprints",
            json=batch,
            headers={"X-API-Key": self.api_key},
            catch_response=True
        ) as response:
            if response.status_code == 202:
                response.success()
            elif response.status_code in [429]:
                # Rate limit is expected under high load
                response.success()
            else:
                response.failure(f"Unexpected status {response.status_code}")

    @task(1)
    def health_check(self):
        """GET /health"""
        with self.client.get("/health", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Health check failed: {response.status_code}")


class HighThroughputIngestUser(FastHttpUser):
    """
    Simulates extremely high throughput device sending.
    Used for stress testing and throughput measurements.
    """
    wait_time = between(0.001, 0.01)  # Very rapid fire
    api_key = "test_ingest_key_12345"

    def on_start(self):
        """Generate device ID."""
        self.device_id = "a" * 64

    def generate_batch(self):
        """Minimal batch for high throughput."""
        return {
            "device_id": self.device_id,
            "fingerprints": [
                {
                    "network": "espn",
                    "fingerprint": "f" * 64,
                    "timestamp": int(time.time()),
                    "confidence": 0.95
                }
            ]
        }

    @task
    def send_fingerprints(self):
        """Send fingerprints at maximum throughput."""
        batch = self.generate_batch()
        self.client.post(
            "/v1/fingerprints",
            json=batch,
            headers={"X-API-Key": self.api_key}
        )


class DSPUser(HttpUser):
    """
    Simulates DSPs and ad platforms doing real-time device lookups.
    Expected: <5ms latency, high QPS (thousands per second).
    Uses advertiser-api as base URL.
    """
    wait_time = between(0.0001, 0.001)  # Very high throughput: 1000-10000 req/sec
    host = "http://localhost:8084"  # advertiser-api
    oauth_token = "test_oauth_token_12345"

    def on_start(self):
        """Setup DSP user context."""
        self.request_count = 0
        self.latencies = []

    def generate_device_lookup(self):
        """Generate a realistic OpenRTB-like lookup request."""
        device_id = "d" * 63 + str(random.randint(0, 9))
        ip = f"192.168.{random.randint(0, 255)}.{random.randint(1, 254)}"
        return {
            "device": {
                "id": device_id,
                "ip": ip,
                "ua": "Mozilla/5.0 (Linux; U; Android 11; en-US) AppleWebKit/537.36"
            },
            "user": {
                "id": f"user_{random.randint(1000000, 9999999)}"
            },
            "site": {
                "id": f"site_{random.randint(1, 100)}",
                "name": "example.com"
            }
        }

    @task(95)
    def rtb_lookup(self):
        """POST /v1/sync/openrtb - Critical real-time lookup"""
        payload = self.generate_device_lookup()
        start_time = time.time()

        with self.client.post(
            "/v1/sync/openrtb",
            json=payload,
            headers={"Authorization": f"Bearer {self.oauth_token}"},
            catch_response=True
        ) as response:
            latency = (time.time() - start_time) * 1000  # ms
            self.latencies.append(latency)

            if response.status_code == 200:
                response.success()
                if latency > 5.0:
                    response.failure(f"Latency {latency:.2f}ms exceeds 5ms SLA")
            else:
                response.failure(f"Status {response.status_code}")

    @task(5)
    def get_segments(self):
        """GET /v1/segments - Pre-call segment list fetch"""
        with self.client.get(
            "/v1/segments",
            headers={"Authorization": f"Bearer {self.oauth_token}"},
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Status {response.status_code}")


class HighFrequencyDSPUser(FastHttpUser):
    """
    Simulates ultra-high frequency DSP lookups using FastHttpUser.
    Optimized for throughput measurement: 10K+ req/sec per instance.
    """
    wait_time = between(0.00001, 0.0001)
    host = "http://localhost:8084"
    oauth_token = "test_oauth_token_12345"

    @task
    def rtb_lookup(self):
        """Ultra-high frequency RTB lookup."""
        payload = {
            "device": {
                "id": "a" * 64,
                "ip": "192.168.1.100"
            }
        }
        self.client.post(
            "/v1/sync/openrtb",
            json=payload,
            headers={"Authorization": f"Bearer {self.oauth_token}"}
        )


class SegmentManagementUser(HttpUser):
    """
    Simulates advertiser/DSP users managing segments.
    Lower frequency: creating, updating, querying segments.
    """
    wait_time = between(5, 30)
    host = "http://localhost:8084"
    oauth_token = "test_oauth_token_12345"

    def on_start(self):
        """Initialize test data."""
        self.segment_ids = []

    def generate_segment_dsl(self):
        """Generate a valid segment DSL."""
        networks = ["espn", "hbo", "netflix", "cnn", "bbc"]
        return {
            "rules": [
                {
                    "network": random.choice(networks),
                    "operator": "include"
                },
                {
                    "network": random.choice(networks),
                    "operator": "include"
                }
            ],
            "logic": "OR"
        }

    @task(3)
    def create_custom_segment(self):
        """POST /v1/segments - Create a custom audience segment"""
        payload = {
            "name": f"Test Segment {int(time.time())}",
            "description": "Load test segment",
            "dsl": self.generate_segment_dsl(),
            "cpm_floor": 5.00
        }
        with self.client.post(
            "/v1/segments",
            json=payload,
            headers={"Authorization": f"Bearer {self.oauth_token}"},
            catch_response=True
        ) as response:
            if response.status_code == 201:
                data = response.json()
                if "segment_id" in data:
                    self.segment_ids.append(data["segment_id"])
                response.success()
            else:
                response.failure(f"Status {response.status_code}")

    @task(1)
    def list_segments(self):
        """GET /v1/segments - List available segments"""
        with self.client.get(
            "/v1/segments",
            headers={"Authorization": f"Bearer {self.oauth_token}"},
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Status {response.status_code}")

    @task(1)
    def get_segment_size(self):
        """GET /v1/segments/{id}/size - Get segment audience size"""
        if self.segment_ids:
            segment_id = random.choice(self.segment_ids)
            with self.client.get(
                f"/v1/segments/{segment_id}/size",
                headers={"Authorization": f"Bearer {self.oauth_token}"},
                catch_response=True
            ) as response:
                if response.status_code == 200:
                    response.success()
                else:
                    response.failure(f"Status {response.status_code}")


class PrivacyComplianceUser(HttpUser):
    """
    Simulates privacy and compliance operations.
    Lower frequency: opt-outs, consent recording, data exports.
    """
    wait_time = between(10, 60)
    host = "http://localhost:8085"
    oauth_token = "test_oauth_token_12345"

    def generate_device_id(self):
        """Generate a random device ID."""
        random_bytes = "".join(format(random.randint(0, 255), '02x') for _ in range(32))
        return random_bytes

    @task(7)
    def record_consent(self):
        """POST /v1/consent/record - Record user consent"""
        payload = {
            "device_id": self.generate_device_id(),
            "consent_version": "1.0",
            "consents": {
                "personalization": random.choice([True, False]),
                "analytics": random.choice([True, False]),
                "marketing": random.choice([True, False])
            },
            "timestamp": int(time.time())
        }
        with self.client.post(
            "/v1/consent/record",
            json=payload,
            headers={"Authorization": f"Bearer {self.oauth_token}"},
            catch_response=True
        ) as response:
            if response.status_code in [200, 201]:
                response.success()
            else:
                response.failure(f"Status {response.status_code}")

    @task(2)
    def opt_out_device(self):
        """POST /v1/privacy/opt-out - Opt out device from tracking"""
        payload = {
            "device_id": self.generate_device_id(),
            "reason": "user_request"
        }
        with self.client.post(
            "/v1/privacy/opt-out",
            json=payload,
            headers={"Authorization": f"Bearer {self.oauth_token}"},
            catch_response=True
        ) as response:
            if response.status_code in [202, 204]:
                response.success()
            else:
                response.failure(f"Status {response.status_code}")

    @task(1)
    def data_export(self):
        """GET /v1/privacy/data-export - Export user data"""
        device_id = self.generate_device_id()
        with self.client.get(
            "/v1/privacy/data-export",
            params={"device_id": device_id},
            headers={"Authorization": f"Bearer {self.oauth_token}"},
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Status {response.status_code}")


# Event handlers for custom reporting
@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Called when Locust test starts."""
    print("\n" + "="*80)
    print("Synora Load Test Started")
    print("="*80)


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Called when Locust test stops."""
    print("\n" + "="*80)
    print("Synora Load Test Completed")
    print("="*80)
    print(f"Total requests: {environment.stats.total.num_requests}")
    print(f"Total failures: {environment.stats.total.num_failures}")
    if environment.stats.total.num_requests > 0:
        failure_rate = (environment.stats.total.num_failures / environment.stats.total.num_requests) * 100
        print(f"Failure rate: {failure_rate:.2f}%")
