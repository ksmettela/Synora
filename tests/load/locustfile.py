"""
Load tests for Synora platform using Locust.

Run with:
  locust -f tests/load/locustfile.py --headless -u 100 -r 10 --run-time 60s
"""
from locust import HttpUser, task, between, events
import hashlib
import random
import time
import json


def random_device_id():
    """Generate a random device ID."""
    return hashlib.sha256(str(random.random()).encode()).hexdigest()


def random_fingerprint():
    """Generate a random fingerprint hash."""
    return hashlib.sha256(str(random.random()).encode()).hexdigest()


class IngestUser(HttpUser):
    """
    Simulates embedded SDK devices sending fingerprint batches.
    Tests the ingestor service under load.
    """
    host = "http://localhost:8080"
    wait_time = between(0.05, 0.1)  # 10-20 req/sec per user

    def on_start(self):
        """Initialize user session."""
        self.device_ids = [random_device_id() for _ in range(20)]

    @task(10)
    def send_fingerprint_batch(self):
        """Send a batch of fingerprints (10x frequency)."""
        batch = [
            {
                "device_id": random.choice(self.device_ids),
                "fingerprint_hash": random_fingerprint(),
                "timestamp_utc": int(time.time()),
                "manufacturer": random.choice(["LG", "Vizio", "TCL", "Sony", "Hisense"]),
                "model": f"Model-{random.randint(1000, 9999)}",
                "ip_address": f"192.168.{random.randint(1, 254)}.{random.randint(1, 254)}"
            }
            for _ in range(random.randint(5, 20))
        ]
        self.client.post(
            "/v1/fingerprints",
            json={"batch": batch},
            headers={"X-API-Key": "load-test-key"},
            name="/v1/fingerprints"
        )

    @task(1)
    def health_check(self):
        """Periodic health check (1x frequency)."""
        self.client.get("/health", name="/health")


class DSPUser(HttpUser):
    """
    Simulates DSPs doing real-time RTB device lookups.
    Tests the advertiser API service under load.
    """
    host = "http://localhost:8084"
    wait_time = between(0.001, 0.005)  # 200-1000 req/sec per user

    def on_start(self):
        """Initialize user session and authenticate."""
        # Get auth token
        resp = self.client.post(
            "/v1/auth/token",
            json={
                "client_id": "load-test-dsp",
                "client_secret": "load-test-secret",
                "grant_type": "client_credentials"
            }
        )
        if resp.status_code == 200:
            self.token = resp.json().get("access_token", "")
        else:
            self.token = ""

        # Pre-populate device pool for lookups
        self.device_pool = [random_device_id() for _ in range(10000)]

    @task(20)
    def rtb_lookup(self):
        """RTB OpenRTB lookup (20x frequency)."""
        device_id = random.choice(self.device_pool)
        self.client.post(
            "/v1/sync/openrtb",
            json={
                "device_id": device_id,
                "ip": f"10.{random.randint(1, 254)}.{random.randint(1, 254)}.{random.randint(1, 254)}"
            },
            headers={"Authorization": f"Bearer {self.token}"},
            name="/v1/sync/openrtb"
        )

    @task(2)
    def list_segments(self):
        """List available segments (2x frequency)."""
        self.client.get(
            "/v1/segments",
            headers={"Authorization": f"Bearer {self.token}"},
            name="/v1/segments"
        )

    @task(1)
    def get_segment_size(self):
        """Get segment size estimate (1x frequency)."""
        # Use a predefined segment ID
        self.client.get(
            "/v1/segments/sports_enthusiasts/size",
            headers={"Authorization": f"Bearer {self.token}"},
            name="/v1/segments/{id}/size"
        )


class IndexerUser(HttpUser):
    """
    Simulates fingerprint indexer operations.
    Tests the indexer service under load.
    """
    host = "http://localhost:8082"
    wait_time = between(0.05, 0.2)  # 5-20 req/sec per user

    def on_start(self):
        """Initialize with some known fingerprints."""
        self.indexed_fps = [random_fingerprint() for _ in range(100)]

    @task(3)
    def index_fingerprint(self):
        """Index new fingerprints (3x frequency)."""
        self.client.post(
            "/v1/fingerprints/index",
            json={
                "fingerprint_hash": random_fingerprint(),
                "content_id": f"content-{int(time.time())}-{random.randint(1000, 9999)}",
                "title": f"Content {random.randint(1, 1000)}",
                "network": random.choice(["HBO", "NBC", "ESPN", "CNN", "FOX"]),
                "genre": random.choice(["Drama", "Sports", "News", "Entertainment", "Documentary"]),
                "duration_seconds": random.randint(1800, 7200),
                "aired_at_utc": int(time.time())
            },
            name="/v1/fingerprints/index"
        )

    @task(5)
    def lookup_fingerprint(self):
        """Lookup fingerprints (5x frequency)."""
        fp = random.choice(self.indexed_fps)
        self.client.post(
            "/v1/fingerprints/lookup",
            json={"fingerprint_hash": fp},
            name="/v1/fingerprints/lookup"
        )

    @task(1)
    def get_stats(self):
        """Get indexer stats (1x frequency)."""
        self.client.get(
            "/v1/fingerprints/stats",
            name="/v1/fingerprints/stats"
        )


class PrivacyUser(HttpUser):
    """
    Simulates privacy operations.
    Tests the privacy service under load.
    """
    host = "http://localhost:8085"
    wait_time = between(0.05, 0.15)  # 7-20 req/sec per user

    def on_start(self):
        """Initialize with test devices."""
        self.test_devices = [random_device_id() for _ in range(100)]

    @task(5)
    def record_consent(self):
        """Record consent (5x frequency)."""
        device = random.choice(self.test_devices)
        self.client.post(
            "/v1/consent/record",
            json={
                "device_id": device,
                "opted_in": random.choice([True, False]),
                "consent_timestamp_utc": int(time.time())
            },
            name="/v1/consent/record"
        )

    @task(3)
    def get_consent(self):
        """Get consent status (3x frequency)."""
        device = random.choice(self.test_devices)
        self.client.get(
            f"/v1/consent/{device}",
            name="/v1/consent/{device_id}"
        )

    @task(1)
    def opt_out(self):
        """Opt-out device (1x frequency)."""
        device = random.choice(self.test_devices)
        self.client.post(
            "/v1/privacy/opt-out",
            json={"device_id": device},
            name="/v1/privacy/opt-out"
        )


# Event handlers for load test reporting
@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Called when load test starts."""
    print("Load test starting...")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Called when load test stops."""
    print("Load test stopped")
    print(f"\nLoad test statistics:")
    print(f"Total requests: {environment.stats.total.num_requests}")
    print(f"Total failures: {environment.stats.total.num_failures}")
    print(f"Response time p50: {environment.stats.total.get_response_time_percentile(0.5):.0f}ms")
    print(f"Response time p95: {environment.stats.total.get_response_time_percentile(0.95):.0f}ms")
    print(f"Response time p99: {environment.stats.total.get_response_time_percentile(0.99):.0f}ms")
