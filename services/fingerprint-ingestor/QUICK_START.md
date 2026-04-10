# Quick Start Guide - Fingerprint Ingestor

## 5-Minute Setup

### Prerequisites
- Docker & Docker Compose installed
- X-API-Key for authentication

### Start Everything
```bash
cd /Users/kumarswamymettela/Downloads/Side\ Projects/Synora/acraas/services/fingerprint-ingestor/

# Start full stack (Kafka, Redis, Ingestor)
make docker-up

# Verify it's running
curl http://localhost:8080/health
```

### Test Ingestion
```bash
# Add a test API key
docker exec $(docker ps -q -f label=com.docker.compose.service=redis) \
  redis-cli SADD valid_api_keys test-key

# Send a fingerprint batch
curl -X POST http://localhost:8080/v1/fingerprints \
  -H "X-API-Key: test-key" \
  -H "Content-Type: application/json" \
  -d '{
    "batch": [
      {
        "device_id": "a0000000000000000000000000000000000000000000000000000000000000",
        "fingerprint_hash": "b1111111111111111111111111111111111111111111111111111111111111",
        "timestamp_utc": '$(date +%s)'000,
        "manufacturer": "LG",
        "model": "OLED55C3",
        "ip_address": "192.168.1.1"
      }
    ]
  }'

# Expected response: 202 Accepted
```

### Monitor Metrics
```bash
# Health check
curl http://localhost:8080/health

# Prometheus metrics
curl http://localhost:9090/metrics | grep acraas
```

### Logs
```bash
# View service logs
make docker-logs

# Or
docker-compose logs -f fingerprint-ingestor
```

## Common Commands

```bash
# Build production image
make docker-build

# Run unit tests
go test -v ./...

# Run integration tests (requires running services)
go test -v -tags=integration ./tests/...

# Load test
./scripts/load-test.sh 1000 10 50

# Stop everything
make docker-down

# Clean up
make clean
```

## Configuration

Set environment variables before starting:
```bash
# Default config (see .env.example)
export KAFKA_BOOTSTRAP_SERVERS=kafka:9092
export REDIS_URL=redis://redis:6379
export RATE_LIMIT_PER_SECOND=10000
export MAX_BATCH_SIZE=100
```

## API Endpoints

```bash
# Ingest fingerprints
POST /v1/fingerprints
Headers: X-API-Key: <key>
Body: { "batch": [...] }
Response: 202 Accepted

# Health check
GET /health
Response: 200 OK

# Prometheus metrics
GET /metrics (on port :9090)
Response: 200 OK
```

## Validation Rules

- **device_id**: 64-char hex (SHA-256)
- **fingerprint_hash**: 64-char hex
- **timestamp_utc**: Within 5 minutes of now (milliseconds)
- **ip_address**: Not from datacenter (AWS, GCP, Azure, etc.)
- **batch**: 1-100 items per request

## Kafka Topic

Topic: `raw.fingerprints`

Message schema:
```json
{
  "device_id": "hex",
  "fingerprint_hash": "hex",
  "timestamp_utc": 1234567890000,
  "manufacturer": "LG",
  "model": "OLED55C3",
  "ip_address": "203.0.113.42",
  "ingested_at": 1234567890123
}
```

## Troubleshooting

### Service won't start
```bash
# Check logs
make docker-logs

# Verify dependencies
docker-compose ps

# Verify ports available
lsof -i :8080
lsof -i :9090
```

### Can't connect to Kafka
```bash
# Test Kafka connectivity
docker exec $(docker ps -q -f label=com.docker.compose.service=kafka) \
  kafka-broker-api-versions --bootstrap-server kafka:9092
```

### Can't connect to Redis
```bash
# Test Redis connectivity
docker exec $(docker ps -q -f label=com.docker.compose.service=redis) \
  redis-cli PING
```

### Rate limiting rejections
```bash
# Check rate limit for API key
docker exec $(docker ps -q -f label=com.docker.compose.service=redis) \
  redis-cli KEYS "ratelimit:*"

# Clear rate limits (for testing)
docker exec $(docker ps -q -f label=com.docker.compose.service=redis) \
  redis-cli FLUSHDB
```

## Next Steps

1. **Read full documentation**: See [README.md](README.md)
2. **Understand API**: See [API.md](API.md)
3. **Review implementation**: See [IMPLEMENTATION.md](IMPLEMENTATION.md)
4. **Run benchmarks**: `go test -bench=. ./tests/...`
5. **Deploy to production**: See deployment examples in README.md

## Performance Tips

- Default throughput: 500K+ requests/second
- Tune based on your infrastructure
- Monitor metrics: `http://localhost:9090/metrics`
- Adjust concurrency if needed (see main.go MaxConns, Concurrency)

## Security Notes

- Change default API keys in production
- Use HTTPS in production (configure reverse proxy)
- Restrict Redis access to internal network only
- Keep GeoIP database updated monthly
- Use strong API key values (32+ chars random)

## Production Deployment

```bash
# Build production image
docker build -t acraas/fingerprint-ingestor:1.0.0 .

# Push to registry
docker push acraas/fingerprint-ingestor:1.0.0

# Deploy with Docker Swarm, Kubernetes, or cloud platform
# See README.md for examples
```

---

Need help? Check the full documentation or run `make help` for all available targets.
