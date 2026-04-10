# Synora Integration and Load Test Suite

Complete test suite for the Synora platform, including integration tests, end-to-end tests, and load tests.

## Test Structure

```
tests/
├── integration/           # Integration tests (require running services)
│   ├── conftest.py       # Pytest fixtures and configuration
│   ├── test_ingestor.py  # Fingerprint ingestor service tests
│   ├── test_indexer.py   # Fingerprint indexer service tests
│   ├── test_advertiser_api.py  # DSP/advertiser API tests
│   ├── test_privacy.py   # Privacy service tests
│   └── test_end_to_end.py # Full pipeline tests
├── load/
│   └── locustfile.py     # Load tests using Locust
├── requirements.txt      # Python dependencies
├── pytest.ini           # Pytest configuration
└── README.md            # This file
```

## Prerequisites

### 1. Running Services

Before running tests, ensure all Synora services are running:

```bash
# Start all services with docker-compose
docker-compose up -d

# Verify services are healthy
./health-check.sh
```

Required services:
- **Fingerprint Ingestor** (Component B) - http://localhost:8080
- **Fingerprint Indexer** (Component C1) - http://localhost:8082
- **Advertiser API** (Component F) - http://localhost:8084
- **Privacy Service** (Component G) - http://localhost:8085
- **Billing Service** (Component H) - http://localhost:8086
- **Kafka** - localhost:9092
- **Redis** - localhost:6379

### 2. Environment Configuration

Set environment variables for test services (optional, defaults provided):

```bash
export INGEST_BASE_URL="http://localhost:8080"
export INDEXER_BASE_URL="http://localhost:8082"
export API_BASE_URL="http://localhost:8084"
export PRIVACY_BASE_URL="http://localhost:8085"
export BILLING_BASE_URL="http://localhost:8086"
export KAFKA_BOOTSTRAP_SERVERS="localhost:9092"
export REDIS_URL="redis://localhost:6379"
export TEST_API_KEY="test-api-key-001"
export TEST_CLIENT_ID="test-client-001"
export TEST_CLIENT_SECRET="test-client-secret-001"
```

### 3. Install Test Dependencies

```bash
pip install -r tests/requirements.txt
```

## Running Tests

### Fast Integration Tests (exclude slow tests)

Run all integration tests except slow end-to-end tests:

```bash
pytest tests/integration/ -m "not slow" -v
```

This runs ~80 tests in under 2 minutes, testing:
- Health check endpoints
- Fingerprint ingestion and validation
- API authentication
- Rate limiting
- Fingerprint indexing and matching
- Segment management
- RTB lookups
- Privacy and consent management
- GDPR compliance
- TCF consent strings

Expected output:
```
tests/integration/test_ingestor.py::TestHealth::test_health_returns_200 PASSED
tests/integration/test_ingestor.py::TestFingerprintIngestion::test_valid_single_fingerprint_returns_202 PASSED
...
======================== 82 passed in 1m 45s ========================
```

### Full Integration Tests (including slow tests)

Run complete integration test suite including full pipeline tests:

```bash
pytest tests/integration/ -m slow -v
```

This includes:
- Full fingerprint ingestion → Kafka pipeline verification
- Complete opt-out lifecycle
- Segment creation and RTB lookup integration

Estimated runtime: 5-10 minutes

### Run Specific Test Class

```bash
pytest tests/integration/test_ingestor.py::TestFingerprintIngestion -v
pytest tests/integration/test_advertiser_api.py::TestRTBLookup -v
pytest tests/integration/test_privacy.py::TestOptOut -v
```

### Run Single Test

```bash
pytest tests/integration/test_ingestor.py::TestHealth::test_health_returns_200 -v
```

### Run with Verbose Output

```bash
pytest tests/integration/ -vv --tb=long
```

### Run with Coverage Report

```bash
pytest tests/integration/ --cov=services --cov-report=html
```

## Load Testing

### Install Locust (if not already installed)

```bash
pip install locust==2.20.0
```

### Run Load Test

Simulates 100 concurrent users (10 ramp-up rate) for 60 seconds:

```bash
locust -f tests/load/locustfile.py --headless -u 100 -r 10 --run-time 60s
```

### Load Test Configuration Options

- `-u 100` - Number of concurrent users (default: 1)
- `-r 10` - User ramp-up rate (users spawned per second, default: 1)
- `--run-time 60s` - Total test duration (default: unlimited)
- `-H http://localhost:8080` - Override host URL

### Simulated User Types

1. **IngestUser** - Simulates SDK devices sending fingerprint batches
   - 10-20 requests/sec per user
   - Tasks: send_fingerprint_batch (10x), health_check (1x)

2. **DSPUser** - Simulates real-time RTB lookups
   - 200-1000 requests/sec per user
   - Tasks: rtb_lookup (20x), list_segments (2x), get_segment_size (1x)

3. **IndexerUser** - Simulates fingerprint indexing operations
   - 5-20 requests/sec per user
   - Tasks: index_fingerprint (3x), lookup_fingerprint (5x), get_stats (1x)

4. **PrivacyUser** - Simulates privacy operations
   - 7-20 requests/sec per user
   - Tasks: record_consent (5x), get_consent (3x), opt_out (1x)

### Load Test Results

After completion, Locust reports:
- Total requests and failures
- Response time percentiles (p50, p95, p99)
- Requests per second
- Failure rate by endpoint

Example output:
```
Load test statistics:
Total requests: 50000
Total failures: 12
Response time p50: 45ms
Response time p95: 120ms
Response time p99: 250ms
```

## Fixture Reference

### Authentication
- `auth_token` - Returns valid Bearer token for API calls

### Device/Fingerprint Data
- `test_device_id` - Random valid device ID (64-char hex SHA256)
- `test_fingerprint` - Random valid fingerprint hash
- `reference_fingerprint` - Pre-indexed fingerprint tuple (hash, content_id, title, network, genre)

### Service Clients (session-scoped)
- `ingest_client` - httpx.Client for ingestor service
- `indexer_client` - httpx.Client for indexer service
- `api_client` - httpx.Client for advertiser API
- `privacy_client` - httpx.Client for privacy service
- `billing_client` - httpx.Client for billing service

### Infrastructure
- `redis_client` - Connected Redis client (skips test if unavailable)
- `kafka_consumer(topic)` - Factory for Kafka consumers (skips if unavailable)
- `wait_for_service(url, timeout)` - Polls /health until ready

### Test Data
- `valid_batch_payload` - Pre-built valid fingerprint batch
- `random_fingerprints` - List of 100 random fingerprints

## Test Markers

Tests are marked for targeted execution:

### Integration Tests
```bash
pytest -m integration tests/
```

### Slow Tests (full pipeline, >10s)
```bash
pytest -m slow tests/
```

### Exclude Slow Tests
```bash
pytest -m "not slow" tests/
```

### Unit Tests Only
```bash
pytest -m unit tests/
```

## Troubleshooting

### "Redis unavailable" error
- Ensure Redis is running: `docker-compose ps redis`
- Tests will automatically skip if Redis unavailable
- Force run with: `pytest --tb=short` to see which services are missing

### "Kafka unavailable" error
- Ensure Kafka is running: `docker-compose ps kafka`
- Tests using `kafka_consumer` fixture will skip if unavailable

### Connection timeouts
- Verify service URLs in environment variables match running services
- Check firewall rules allow localhost connections
- Increase timeout with: `pytest --timeout=120`

### Rate limiting tests fail
- Some rate limit tests may be flaky depending on system load
- Run individually: `pytest tests/integration/test_ingestor.py::TestRateLimiting -v`

### Tests fail with "invalid API key"
- Verify `TEST_API_KEY` environment variable matches service configuration
- Default: `test-api-key-001`

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Synora Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      kafka:
        image: confluentinc/cp-kafka:7.4.0
        ...
      redis:
        image: redis:7.0
        ...

    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: 3.11

      - name: Install dependencies
        run: pip install -r tests/requirements.txt

      - name: Run integration tests
        run: pytest tests/integration/ -m "not slow" --tb=short

      - name: Run slow tests
        run: pytest tests/integration/ -m slow --tb=short
```

## Test Coverage

### Components Tested

| Component | Test File | Coverage |
|-----------|-----------|----------|
| Ingestor (B) | test_ingestor.py | Health, validation, auth, rate limit, Kafka |
| Indexer (C1) | test_indexer.py | Indexing, matching, hamming distance, stats |
| Advertiser API (F) | test_advertiser_api.py | OAuth2, segments, RTB lookups, overlap |
| Privacy Service (G) | test_privacy.py | Consent, opt-out, GDPR, TCF, erasure |
| End-to-End | test_end_to_end.py | Full pipelines, opt-out lifecycle |

### Test Counts

- **Fast Integration Tests**: ~82 tests
- **Slow Tests**: ~3 tests
- **Load Test**: 4 user types, 400+ simultaneous scenarios

## Best Practices

1. **Run fast tests before slow**: `pytest -m "not slow" && pytest -m slow`

2. **Use markers for CI/CD**: Skip slow tests in CI, run them on-demand

3. **Monitor Redis/Kafka**: Some tests depend on these services
   ```bash
   docker-compose logs -f redis kafka
   ```

4. **Check service health**: Run health-check before tests
   ```bash
   curl http://localhost:8080/health
   curl http://localhost:8082/health
   curl http://localhost:8084/health
   ```

5. **Load test gradually**: Start with small user count before scaling
   ```bash
   locust -f tests/load/locustfile.py -u 10 -r 1 --run-time 30s
   locust -f tests/load/locustfile.py -u 100 -r 10 --run-time 60s
   ```

## Contributing

When adding new tests:

1. Place in appropriate file (test_component.py)
2. Add `@pytest.mark.integration` decorator
3. Use `@pytest.mark.slow` for tests >2 seconds
4. Document expected behavior with docstrings
5. Use fixtures from conftest.py
6. Clean up resources (close clients, etc.)

## Support

For issues or questions:
1. Check test logs: `pytest -vv --tb=long`
2. Review service health: `./health-check.sh`
3. Check environment variables: `env | grep _BASE_URL`
4. Review service logs: `docker-compose logs service-name`
